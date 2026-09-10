import unittest
from uuid import uuid4
from pydantic import ValidationError
from app.schemas.expense import ExpenseCreate, ExpenseUpdate
from app.schemas.group import GroupCreate, GroupUpdate
from app.schemas.user import UserCreate
from app.routes.payments import PaymentCreate

class ValidationTest(unittest.TestCase):
    def test_money_rules_match_for_create_edit_and_payment(self):
        factories = [lambda amount: ExpenseCreate(description='Cena', amount=amount, payer_id=1, group_id=1, participants=[1]), lambda amount: ExpenseUpdate(description='Cena', amount=amount, payer_id=1, participants=[1]), lambda amount: PaymentCreate(amount=amount, group_id=1, from_user_id=1, to_user_id=2, payment_date='2026-09-08', request_id=uuid4())]
        for factory in factories:
            for amount in ('0.01', '99999999.99'):
                factory(amount)
            for amount in ('0', '-1', '0.001', '100000000', 'NaN', 'Infinity'):
                with self.assertRaises(ValidationError):
                    factory(amount)

    def test_names_and_optional_email(self):
        for factory, limit in [(lambda name: UserCreate(name=name), 100), (lambda name: GroupCreate(name=name, owner_id=1), 150), (lambda name: GroupUpdate(name=name), 150)]:
            self.assertEqual(factory('  Ana  ').name, 'Ana')
            factory('a' * limit)
            for name in ('   ', 'a' * (limit + 1)):
                with self.assertRaises(ValidationError):
                    factory(name)
        self.assertIsNone(UserCreate(name='Ana', email=' ').email)
        with self.assertRaises(ValidationError):
            UserCreate(name='Ana', email='incorrecto')
