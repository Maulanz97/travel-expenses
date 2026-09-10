import unittest
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.database import Base
from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.expense import Expense
from app.models.expense_participant import ExpenseParticipant
from app.routes.expenses import create_expense
from app.schemas.expense import ExpenseCreate


class ExpenseRetryTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add_all([User(id=1, name='Ana'), User(id=2, name='Luis'), Group(id=1, name='Viaje')])
        self.db.commit()
        self.db.add_all([GroupMember(group_id=1, user_id=i, role='member') for i in (1, 2)])
        self.db.commit()
        self.payload = dict(request_id=str(uuid4()), description='Cena', amount='10.00', payer_id=1,
                            group_id=1, participants=[1, 2], custom_shares={1: '3.00', 2: '7.00'})

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_lost_response_retries_preserve_one_expense_and_split(self):
        first = create_expense(ExpenseCreate(**self.payload), self.db)
        self.db.close()
        self.db = Session(self.engine)
        retry = create_expense(ExpenseCreate(**{**self.payload, 'amount': '10'}), self.db)
        self.assertEqual(first['id'], retry['id'])
        self.assertEqual(self.db.query(Expense).count(), 1)
        self.assertEqual(self.db.query(ExpenseParticipant).count(), 2)
        self.assertEqual(self.db.get(Expense, first['id']).custom_shares, {'1': '3.00', '2': '7.00'})

    def test_replay_after_edit_or_void_does_not_restore_original(self):
        first = create_expense(ExpenseCreate(**self.payload), self.db)
        expense = self.db.get(Expense, first['id'])
        expense.description = 'Cena corregida'
        expense.voided = True
        self.db.commit()
        self.assertEqual(create_expense(ExpenseCreate(**self.payload), self.db)['id'], first['id'])
        self.assertEqual(expense.description, 'Cena corregida')
        self.assertTrue(expense.voided)
        with self.assertRaises(HTTPException) as conflict:
            create_expense(ExpenseCreate(**{**self.payload, 'description': 'Otro gasto'}), self.db)
        self.assertEqual(conflict.exception.status_code, 409)

    def test_database_rejects_duplicate_identity(self):
        create_expense(ExpenseCreate(**self.payload), self.db)
        self.db.add(Expense(request_id=self.payload['request_id'], description='Duplicado', amount=10, payer_id=1, group_id=1))
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()
        self.assertEqual(self.db.query(Expense).count(), 1)

    def test_failed_transaction_can_retry_same_identity(self):
        with self.engine.begin() as connection:
            connection.exec_driver_sql("CREATE TRIGGER fail_split BEFORE INSERT ON expense_participants BEGIN SELECT RAISE(ABORT, 'failed split'); END")
        with self.assertRaises(IntegrityError):
            create_expense(ExpenseCreate(**self.payload), self.db)
        self.assertEqual(self.db.query(Expense).count(), 0)
        with self.engine.begin() as connection:
            connection.exec_driver_sql('DROP TRIGGER fail_split')
        first = create_expense(ExpenseCreate(**self.payload), self.db)
        self.assertEqual(create_expense(ExpenseCreate(**self.payload), self.db)['id'], first['id'])
        self.assertEqual(self.db.query(ExpenseParticipant).count(), 2)
