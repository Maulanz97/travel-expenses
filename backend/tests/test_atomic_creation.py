"""Exercise real database failures after the parent INSERT has executed."""
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base
from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.expense import Expense
from app.models.expense_participant import ExpenseParticipant
from app.routes.groups import create_group, get_groups
from app.routes.expenses import create_expense
from app.schemas.group import GroupCreate
from app.schemas.expense import ExpenseCreate
from app.schemas.user import UserCreate
from app.routes.group_members import create_member
from fastapi import HTTPException


class AtomicCreationTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.engine = create_engine(f"sqlite:///{(Path(self.directory.name) / 'test.db').as_posix()}")
        event.listen(self.engine, 'connect', lambda connection, _: connection.execute('PRAGMA foreign_keys=ON'))
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, autoflush=False)
        self.db.add_all([User(id=i, name=f'Persona {i}', email=f'{i}@example.com') for i in (1, 2)])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        self.directory.cleanup()

    def trip(self):
        return create_group(GroupCreate(name='Viaje', owner_id=1), self.db)

    def test_trip_list_counts_members_including_empty_trips(self):
        trip = self.trip()
        self.db.add(Group(name='Sin integrantes'))
        self.db.commit()
        rows = get_groups(self.db)
        self.assertEqual(next(row['member_count'] for row in rows if row['id'] == trip['id']), 1)
        self.assertEqual(next(row['member_count'] for row in rows if row['name'] == 'Sin integrantes'), 0)

    def test_new_organizer_created_with_trip_or_rolled_back(self):
        payload = GroupCreate(name='Nuevo viaje', organizer=UserCreate(name='Nueva organizadora'))
        with self.engine.begin() as connection:
            connection.exec_driver_sql("CREATE TRIGGER fail_new_owner BEFORE INSERT ON group_members BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        with self.assertRaises(IntegrityError):
            create_group(payload, self.db)
        with Session(self.engine) as observer:
            self.assertEqual(observer.query(Group).count(), 0)
            self.assertEqual(observer.query(User).count(), 2)
        with self.engine.begin() as connection:
            connection.exec_driver_sql('DROP TRIGGER fail_new_owner')
        trip = create_group(payload, self.db)
        with Session(self.engine) as observer:
            person = observer.query(User).filter_by(name='Nueva organizadora').one()
            self.assertIsNone(person.email)
            self.assertEqual(observer.query(GroupMember).filter_by(group_id=trip['id'], user_id=person.id, role='owner').count(), 1)

    def test_people_without_email_and_atomic_membership(self):
        trip = self.trip()
        for name in ('Ana', 'Luis'):
            person = create_member(trip['id'], UserCreate(name=name, email='  '), self.db)
            self.assertIsNone(person.email)
            self.assertEqual(self.db.query(GroupMember).filter_by(user_id=person.id, group_id=trip['id']).count(), 1)
        with self.assertRaises(HTTPException):
            create_member(trip['id'], UserCreate(name='Duplicado', email='1@example.com'), self.db)
        with self.engine.begin() as connection:
            connection.exec_driver_sql("CREATE TRIGGER fail_member BEFORE INSERT ON group_members BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        with self.assertRaises(HTTPException):
            create_member(trip['id'], UserCreate(name='No se guarda'), self.db)
        with Session(self.engine) as observer:
            self.assertEqual(observer.query(User).filter_by(name='No se guarda').count(), 0)

    def test_trip_failure_rolls_back_parent_and_session_can_retry(self):
        with self.engine.begin() as connection:
            connection.exec_driver_sql("CREATE TRIGGER fail_owner BEFORE INSERT ON group_members BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        with self.assertRaises(IntegrityError):
            self.trip()
        with Session(self.engine) as observer:
            self.assertEqual(observer.query(Group).count(), 0)
            self.assertEqual(observer.query(GroupMember).count(), 0)
            self.assertEqual(observer.query(User).count(), 2)
        with self.engine.begin() as connection:
            connection.exec_driver_sql('DROP TRIGGER fail_owner')
        trip = self.trip()
        with Session(self.engine) as observer:
            self.assertEqual(observer.query(Group).count(), 1)
            member = observer.query(GroupMember).one()
            self.assertEqual((member.group_id, member.user_id, member.role), (trip['id'], 1, 'owner'))

    def test_expense_failure_on_second_participant_rolls_back_everything(self):
        trip = self.trip()
        self.db.add(GroupMember(group_id=trip['id'], user_id=2, role='member'))
        self.db.commit()
        payload = ExpenseCreate(description='Cena', amount='10.01', payer_id=1, group_id=trip['id'], participants=[1, 2])
        with self.engine.begin() as connection:
            connection.exec_driver_sql("CREATE TRIGGER fail_participant BEFORE INSERT ON expense_participants WHEN NEW.user_id=2 BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        with self.assertRaises(IntegrityError):
            create_expense(payload, self.db)
        with Session(self.engine) as observer:
            self.assertEqual(observer.query(Expense).count(), 0)
            self.assertEqual(observer.query(ExpenseParticipant).count(), 0)
            self.assertEqual(observer.query(GroupMember).count(), 2)
        with self.engine.begin() as connection:
            connection.exec_driver_sql('DROP TRIGGER fail_participant')
        saved = create_expense(payload, self.db)
        with Session(self.engine) as observer:
            self.assertEqual(observer.query(Expense).count(), 1)
            self.assertEqual({p.user_id for p in observer.query(ExpenseParticipant).filter_by(expense_id=saved['id'])}, {1, 2})
