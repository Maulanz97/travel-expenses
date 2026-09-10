import unittest
import tempfile
from pathlib import Path
from alembic.config import Config
from alembic import command
from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.expense import Expense
from app.models.expense_participant import ExpenseParticipant
from app.models.payment import Payment
from app.routes.payments import PaymentCreate, create_payment, void_payment, list_payments
from app.routes.groups import get_group_balances, get_group_settlements
from app.routes.expenses import create_expense, update_expense, void_expense, restore_expense
from app.schemas.expense import ExpenseCreate, ExpenseUpdate


class PaymentsTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add_all([User(id=i, name=f"Persona {i}", email=f"{i}@example.com") for i in [1, 2, 3]])
        self.db.add(Group(id=1, name="Prueba"))
        self.db.commit()
        self.db.add_all([GroupMember(user_id=i, group_id=1, role="member") for i in [1, 2]])
        self.db.commit()
        self.expense = create_expense(ExpenseCreate(description="Cena", amount="1000.00", payer_id=1, group_id=1, participants=[1, 2], expense_date=date(2026, 9, 1)), self.db)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def payload(self, amount="200.00", **kwargs):
        return PaymentCreate(**dict(group_id=1, from_user_id=2, to_user_id=1, amount=amount, payment_date=date(2026, 9, 2), request_id=uuid4(), **kwargs))

    def balances(self):
        return {row["user_id"]: row["balance"] for row in get_group_balances(1, self.db)}

    def test_partial_payment_and_void(self):
        self.assertEqual(self.balances(), {1: Decimal("500"), 2: Decimal("-500")})
        payload = self.payload()
        payment = create_payment(payload, self.db)
        self.assertEqual(self.balances(), {1: Decimal("300"), 2: Decimal("-300")})
        self.assertEqual(get_group_settlements(1, self.db)[0]["amount"], Decimal("300"))
        self.assertEqual(self.db.query(Expense).one().amount, Decimal("1000"))
        self.assertEqual(create_payment(payload, self.db).id, payment.id)
        self.assertEqual(self.db.query(Payment).count(), 1)
        void_payment(payment.id, self.db)
        void_payment(payment.id, self.db)
        self.assertEqual(self.balances()[2], Decimal("-500"))
        self.assertTrue(list_payments(1, self.db)[0]["voided"])

    def test_multiple_payers_edit_void_restore_and_breakdown(self):
        from app.routes.expenses import get_expense_balances
        data = dict(description='Cena', amount='1000', payer_id=1, participants=[2], payer_contributions={1: '700', 2: '300'})
        update_expense(self.expense['id'], ExpenseUpdate(**data), self.db)
        self.assertEqual(self.balances(), {1: Decimal('700'), 2: Decimal('-700')})
        rows = {p['user_id']: p for p in get_expense_balances(self.expense['id'], self.db)}
        self.assertEqual(rows[1]['paid'], Decimal('700'))
        self.assertEqual(rows[2]['paid'], Decimal('300'))
        groups = {p['user_id']: p for p in get_group_balances(1, self.db)}
        self.assertEqual(groups[2]['breakdown']['expenses_paid'], Decimal('300'))
        void_expense(self.expense['id'], self.db)
        self.assertTrue(all(v == 0 for v in self.balances().values()))
        restore_expense(self.expense['id'], self.db)
        self.assertEqual(self.balances()[1], Decimal('700'))
        key = uuid4()
        first = create_expense(ExpenseCreate(**data, group_id=1, request_id=key), self.db)
        self.assertEqual(create_expense(ExpenseCreate(**data, group_id=1, request_id=key), self.db)['id'], first['id'])
        self.assertEqual(self.db.query(Expense).count(), 2)
        for bad in ({1: '700', 2: '200'}, {1: '1000', 2: '0'}, {2: '1000'}):
            with self.assertRaises(ValidationError):
                ExpenseUpdate(**{**data, 'payer_contributions': bad})
        invalid = create_expense(ExpenseCreate(**{**data, 'payer_contributions': {1:'700',3:'300'}}, group_id=1), self.db)
        self.assertIn('message', invalid)
        self.assertEqual(self.db.query(Expense).count(), 2)

    def test_advance_and_later_expenses(self):
        create_payment(self.payload("650"), self.db)
        self.assertEqual(self.balances()[2], Decimal("150"))
        create_expense(ExpenseCreate(description="Transporte", amount="400", payer_id=1, group_id=1, participants=[1, 2]), self.db)
        self.assertEqual(self.balances()[2], Decimal("-50"))
        self.assertEqual(sum(self.balances().values()), 0)

    def test_custom_split_survives_edit_void_restore_and_payments(self):
        from app.routes.expenses import calculate_expense_split
        edit = ExpenseUpdate(description='Personalizado', amount='1000', payer_id=1, participants=[1, 2], custom_shares={1: '700', 2: '300'})
        update_expense(self.expense['id'], edit, self.db)
        self.assertEqual(self.balances(), {1: Decimal('300'), 2: Decimal('-300')})
        self.assertEqual(calculate_expense_split(self.expense['id'], self.db)['shares'][1]['share'], Decimal('300'))
        create_payment(self.payload('200'), self.db)
        self.assertEqual(self.balances()[2], Decimal('-100'))
        void_expense(self.expense['id'], self.db)
        self.assertEqual(self.balances()[2], Decimal('200'))
        restore_expense(self.expense['id'], self.db)
        self.assertEqual(self.balances()[2], Decimal('-100'))
        update_expense(self.expense['id'], ExpenseUpdate(description='Iguales', amount='1000', payer_id=1, participants=[1, 2]), self.db)
        self.assertEqual(self.balances()[2], Decimal('-300'))
        created = create_expense(ExpenseCreate(description='Cero', amount='0.01', payer_id=1, group_id=1, participants=[2], custom_shares={2:'0.01'}), self.db)
        self.assertEqual(self.db.get(Expense, created['id']).custom_shares, {'2': '0.01'})
        for shares in ({1:'999',2:'0'}, {1:'1000'}, {1:'1000.001',2:'0'}, {1:'1001',2:'-1'}):
            with self.assertRaises(ValidationError):
                ExpenseUpdate(description='Inválido', amount='1000', payer_id=1, participants=[1,2], custom_shares=shares)

    def test_expense_edit_void_restore_preserves_payments_and_history(self):
        create_payment(self.payload('500'), self.db)
        update_expense(self.expense['id'], ExpenseUpdate(description='Cena corregida', amount='400', payer_id=1, participants=[1, 2]), self.db)
        self.assertEqual(self.balances(), {1: Decimal('-300'), 2: Decimal('300')})
        expense = self.db.get(Expense, self.expense['id'])
        self.assertEqual(expense.history[0]['before']['amount'], '1000.00')
        self.assertEqual(expense.history[0]['after']['description'], 'Cena corregida')
        void_expense(expense.id, self.db)
        void_expense(expense.id, self.db)
        self.assertEqual(self.balances(), {1: Decimal('-500'), 2: Decimal('500')})
        self.assertEqual(len(expense.history), 2)
        restore_expense(expense.id, self.db)
        self.assertEqual(self.balances()[1], Decimal('-300'))
        self.assertEqual(len(expense.history), 3)
        self.assertEqual(self.db.query(Payment).count(), 1)

    def test_breakdown_reconciles_and_excludes_voided_payments(self):
        payment = create_payment(self.payload(), self.db)
        rows = {item['user_id']: item for item in get_group_balances(1, self.db)}
        self.assertEqual(rows[1]['breakdown'], dict(expenses_paid=Decimal('1000'), expense_share=Decimal('500'), payments_sent=Decimal('0'), payments_received=Decimal('200'), balance=Decimal('300')))
        self.assertEqual(rows[2]['breakdown']['payments_sent'], Decimal('200'))
        void_payment(payment.id, self.db)
        create_expense(ExpenseCreate(description='Solo otra persona', amount='0.01', payer_id=1, group_id=1, participants=[2]), self.db)
        for item in get_group_balances(1, self.db):
            parts = item['breakdown']
            self.assertEqual(parts['payments_sent'] + parts['payments_received'], 0)
            self.assertEqual(parts['expenses_paid'] - parts['expense_share'], item['balance'])
        self.assertEqual(self.balances()[1], Decimal('500.01'))

    def test_movements_reconcile_with_each_total_and_follow_edits_and_voids(self):
        payment = create_payment(self.payload(), self.db)
        update_expense(self.expense['id'], ExpenseUpdate(description='Cena corregida', amount='1000', payer_id=1,
                       participants=[1, 2], custom_shares={1: '0', 2: '1000'}, payer_contributions={1: '700', 2: '300'}), self.db)
        rows = {item['user_id']: item for item in get_group_balances(1, self.db)}
        for item in rows.values():
            for key, movements in item['movements'].items():
                self.assertEqual(sum((m['amount'] for m in movements), Decimal('0')), item['breakdown'][key])
        self.assertEqual(rows[1]['movements']['expenses_paid'][0]['description'], 'Cena corregida')
        self.assertEqual(rows[1]['movements']['expenses_paid'][0]['amount'], Decimal('700'))
        self.assertEqual(rows[1]['movements']['expense_share'][0]['amount'], Decimal('0'))
        self.assertEqual(rows[1]['movements']['payments_received'][0]['description'], 'Pago de Persona 2')
        void_expense(self.expense['id'], self.db)
        rows = get_group_balances(1, self.db)
        self.assertTrue(all(not row['movements']['expenses_paid'] and not row['movements']['expense_share'] for row in rows))
        restore_expense(self.expense['id'], self.db)
        void_payment(payment.id, self.db)
        rows = get_group_balances(1, self.db)
        self.assertTrue(all(not row['movements']['payments_sent'] and not row['movements']['payments_received'] for row in rows))
        self.assertTrue(any(row['movements']['expenses_paid'] for row in rows))

    def test_validation_and_request_conflict(self):
        payload = self.payload()
        create_payment(payload, self.db)
        with self.assertRaises(HTTPException) as caught:
            create_payment(payload.model_copy(update={"amount": Decimal("201")}), self.db)
        self.assertEqual(caught.exception.status_code, 409)
        with self.assertRaises(HTTPException):
            create_payment(payload.model_copy(update={"request_id": uuid4(), "from_user_id": 3}), self.db)
        for amount in ["0", "-2", "1.001"]:
            with self.assertRaises(ValidationError):
                self.payload(amount)
        with self.assertRaises(ValidationError):
            PaymentCreate(**{**payload.model_dump(), "to_user_id": 2})

    def test_expense_date_is_saved_and_preserved_on_legacy_update(self):
        self.assertEqual(self.expense["expense_date"], date(2026, 9, 1))
        update_expense(self.expense["id"], ExpenseUpdate(description="Cena corregida", amount="1000", payer_id=1, participants=[1, 2]), self.db)
        self.assertEqual(self.db.get(Expense, self.expense["id"]).expense_date, date(2026, 9, 1))
        legacy = create_expense(ExpenseCreate(description="Anterior", amount="10", payer_id=1, group_id=1, participants=[1]), self.db)
        self.assertIsNone(legacy["expense_date"])

    def test_consolidated_schema_and_repeat_upgrade(self):
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext
        from sqlalchemy import inspect
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "migration.db"
            config = Config("alembic.ini")
            config.set_main_option("sqlalchemy.url", f"sqlite:///{path.as_posix()}")
            command.upgrade(config, "head")
            engine = create_engine(f"sqlite:///{path.as_posix()}")
            with engine.begin() as connection:
                connection.exec_driver_sql("INSERT INTO users (id,name,email) VALUES (1,'Ana','ana@example.com')")
                connection.exec_driver_sql("INSERT INTO groups (id,name) VALUES (1,'Viaje')")
                connection.exec_driver_sql("INSERT INTO expenses (id,description,amount,payer_id,group_id) VALUES (1,'Anterior',123.45,1,1)")
            command.upgrade(config, "head")
            with engine.connect() as connection:
                self.assertEqual(compare_metadata(MigrationContext.configure(connection, opts={'compare_server_default': True}), Base.metadata), [])
                row = connection.exec_driver_sql("SELECT amount, expense_date FROM expenses WHERE id=1").one()
                self.assertEqual(row[0], 123.45)
                self.assertIsNone(row[1])
                self.assertEqual(connection.exec_driver_sql("SELECT name,email FROM users WHERE id=1").one(), ('Ana', 'ana@example.com'))
                self.assertEqual(connection.exec_driver_sql('PRAGMA foreign_key_check').all(), [])
                connection.exec_driver_sql("INSERT INTO users (name,email) VALUES ('Sin correo',NULL),('Otra persona',NULL)")
            command.downgrade(config, 'base')
            self.assertEqual(set(inspect(engine).get_table_names()), {'alembic_version'})
            command.upgrade(config, 'head')
            with engine.connect() as connection:
                self.assertEqual(connection.exec_driver_sql('SELECT COUNT(*) FROM expenses').scalar(), 0)
                self.assertEqual(compare_metadata(MigrationContext.configure(connection), Base.metadata), [])
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
