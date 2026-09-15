import unittest
from unittest.mock import patch
from uuid import UUID, uuid4
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.expense import Expense
from app.auth import resolve_identity, verify_token


class AccessTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.subjects = {name: str(uuid4()) for name in ('owner', 'writer', 'reader', 'outsider')}
        with Session(self.engine) as db:
            for i, name in enumerate(self.subjects, 1):
                db.add(User(id=i, name=name, login_email=f'{name}@example.com', auth_subject=self.subjects[name]))
            db.add_all([User(id=5, name='Guest', email='guest@example.com'), Group(id=1, name='Privado'), Group(id=2, name='Ajeno')])
            db.commit()
            db.add_all([GroupMember(group_id=1, user_id=1, role='owner'), GroupMember(group_id=1, user_id=2, role='member', can_register_expenses=True), GroupMember(group_id=1, user_id=3, role='member'), GroupMember(group_id=1, user_id=5, role='member'), GroupMember(group_id=2, user_id=4, role='owner')])
            db.commit()
        def database():
            with Session(self.engine, autoflush=False) as db:
                yield db
        app.dependency_overrides[get_db] = database
        def identity(token):
            if token not in self.subjects:
                raise HTTPException(401, 'Invalid token')
            return dict(id=self.subjects[token], email=f'{token}@example.com', email_confirmed_at='2026-01-01', user_metadata={'role': 'owner'})
        self.verifier = patch('app.auth.verify_token', side_effect=identity)
        self.verifier.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.verifier.stop()
        app.dependency_overrides.clear()
        self.engine.dispose()

    def call(self, actor, method, path, body=None):
        return self.client.request(method, path, headers={'Authorization': f'Bearer {actor}'}, json=body)

    def expense(self, **changes):
        return dict(description='Cena', amount='10.00', group_id=1, payer_id=1, participants=[1,2], request_id=str(uuid4()), **changes)

    def test_all_data_requires_session_and_filters_trips(self):
        for path in ('/users/', '/groups/', '/expenses/', '/group-members/group/1', '/groups/1/balances', '/payments/group/1', '/auth/me'):
            self.assertEqual(self.client.get(path).status_code, 401, path)
        self.assertEqual(self.call('invalid', 'GET', '/groups/').status_code, 401)
        self.assertEqual([g['id'] for g in self.call('reader', 'GET', '/groups/').json()], [1])
        self.assertEqual(self.call('reader', 'GET', '/groups/2/balances').status_code, 403)
        self.assertNotIn(4, [u['id'] for u in self.call('reader', 'GET', '/users/').json()])
        self.assertEqual(self.call('reader', 'GET', '/users/4').status_code, 403)

    def test_writer_owns_authorship_and_cannot_edit_other_expenses(self):
        payload = self.expense()
        payload['created_by_id'] = 1
        created = self.call('writer', 'POST', '/expenses/', payload)
        self.assertEqual(created.status_code, 200, created.text)
        eid = created.json()['id']
        with Session(self.engine) as db:
            self.assertEqual(db.get(Expense, eid).created_by_id, 2)
        self.assertEqual(self.call('writer', 'POST', '/expenses/', payload).json()['id'], eid)
        self.assertEqual(self.call('reader', 'POST', '/expenses/', self.expense()).status_code, 403)
        self.assertEqual(self.call('outsider', 'GET', f'/expenses/{eid}').status_code, 403)
        owned = self.call('owner', 'POST', '/expenses/', self.expense()).json()['id']
        for suffix in ('void', 'restore'):
            self.assertEqual(self.call('writer', 'POST', f'/expenses/{owned}/{suffix}').status_code, 403)
        self.assertEqual(self.call('writer', 'PUT', f'/expenses/{owned}', payload).status_code, 403)
        self.assertEqual(self.call('writer', 'POST', '/expense-participants/', {'expense_id': owned, 'user_id': 3}).status_code, 403)
        self.assertEqual(self.call('writer', 'POST', f'/expenses/{eid}/void').status_code, 200)
        self.assertEqual(self.call('owner', 'POST', f'/expenses/{eid}/restore').status_code, 200)

    def test_permissions_only_owner_and_revocation_effective(self):
        path = '/group-members/group/1/access/2'
        body = dict(can_register_expenses=False, login_email='writer@example.com')
        self.assertEqual(self.call('writer', 'PUT', path, body).status_code, 403)
        self.assertEqual(self.call('outsider', 'PUT', path, body).status_code, 403)
        self.assertEqual(self.call('owner', 'PUT', path, body).status_code, 200)
        self.assertEqual(self.call('writer', 'POST', '/expenses/', self.expense()).status_code, 403)
        self.assertEqual(self.call('writer', 'POST', '/payments/', {}).status_code, 422)
        self.assertEqual(self.call('writer', 'POST', '/payments/', {'group_id': 1}).status_code, 403)
        self.assertEqual(self.call('writer', 'POST', '/group-members/', {'group_id':1,'user_id':4,'role':'owner'}).status_code, 403)
        self.assertEqual(self.call('owner', 'POST', '/group-members/', {'group_id':1,'user_id':4,'role':'owner'}).status_code, 403)

    def test_new_trip_organizer_cannot_be_spoofed(self):
        result = self.call('reader', 'POST', '/groups/', {'name':'Nuevo','owner_id':4})
        self.assertEqual(result.status_code, 200)
        with Session(self.engine) as db:
            owner = db.query(GroupMember).filter_by(group_id=result.json()['id'], role='owner').one()
            self.assertEqual(owner.user_id, 3)

    def test_personal_invitation_scoped_to_trip_and_single_use(self):
        path = '/group-members/group/1/access/5/invitation'
        for actor in ('reader', 'writer', 'outsider'):
            self.assertEqual(self.call(actor, 'POST', path).status_code, 403)
        with Session(self.engine) as db:
            db.add(GroupMember(group_id=2, user_id=5, role='member'))
            db.commit()
        first = self.call('owner', 'POST', path).json()['token']
        token = self.call('owner', 'POST', path).json()['token']
        self.assertEqual(self.call('outsider', 'POST', '/invitations/preview', {'token': first}).status_code, 409)
        self.assertEqual(self.call('reader', 'POST', '/invitations/accept', {'token': token}).status_code, 409)
        self.assertEqual(self.client.post('/invitations/accept', json={'token': token}).status_code, 401)
        preview = self.call('outsider', 'POST', '/invitations/preview', {'token': token})
        self.assertEqual(preview.json()['person'], 'Guest')
        self.assertEqual(self.call('outsider', 'POST', '/invitations/accept', {'token': token}).status_code, 200)
        self.assertEqual(self.call('outsider', 'POST', '/invitations/accept', {'token': token}).status_code, 409)
        self.assertEqual(self.call('outsider', 'GET', '/groups/1/balances').status_code, 200)
        self.assertEqual(self.call('outsider', 'POST', '/expenses/', self.expense()).status_code, 403)
        access = {'login_email': 'outsider@example.com', 'can_register_expenses': True}
        self.assertEqual(self.call('owner', 'PUT', '/group-members/group/1/access/5', access).status_code, 200)
        self.assertEqual(self.call('outsider', 'POST', '/expenses/', self.expense()).status_code, 200)
        self.assertEqual(self.call('outsider', 'POST', '/payments/', {'group_id':1}).status_code, 403)
        with Session(self.engine) as db:
            member = db.query(GroupMember).filter_by(group_id=1, user_id=5).one()
            self.assertEqual(member.access_user_id, 4)
            self.assertIsNone(member.invite_hash)
            self.assertIsNone(db.query(GroupMember).filter_by(group_id=2, user_id=5).one().access_user_id)
            self.assertIsNone(db.get(User, 5).auth_subject)

    def test_cancelled_expired_and_removed_member_invitations_fail(self):
        from datetime import datetime, timedelta
        path = '/group-members/group/1/access/5/invitation'
        token = self.call('owner', 'POST', path).json()['token']
        self.assertEqual(self.call('owner', 'DELETE', path).status_code, 200)
        self.assertEqual(self.call('outsider', 'POST', '/invitations/accept', {'token':token}).status_code, 409)
        token = self.call('owner', 'POST', path).json()['token']
        with Session(self.engine) as db:
            member = db.query(GroupMember).filter_by(group_id=1, user_id=5).one()
            self.assertNotEqual(member.invite_hash, token)
            member.invite_expires = datetime.utcnow() - timedelta(seconds=1)
            db.commit()
        self.assertEqual(self.call('outsider', 'POST', '/invitations/accept', {'token':token}).status_code, 409)
        token = self.call('owner', 'POST', path).json()['token']
        self.assertEqual(self.call('owner', 'DELETE', '/group-members/group/1/people/5').status_code, 200)
        self.assertEqual(self.call('outsider', 'POST', '/invitations/accept', {'token':token}).status_code, 409)

    def test_delete_saved_person_checks_ownership_and_trip_membership(self):
        person = self.call('owner', 'POST', '/users/', {'name': 'Error de captura'}).json()
        path = f"/users/{person['id']}"
        self.assertEqual(self.call('outsider', 'DELETE', path).status_code, 403)
        self.assertEqual(self.client.delete(path).status_code, 401)
        self.assertEqual(self.call('owner', 'DELETE', '/users/5').status_code, 409)
        self.assertEqual(self.call('owner', 'DELETE', '/users/1').status_code, 403)
        response = self.call('owner', 'DELETE', path)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {'deleted': True})
        with Session(self.engine) as db:
            self.assertIsNone(db.get(User, person['id']))
            self.assertIsNotNone(db.get(User, 5))

    def test_delete_saved_person_keeps_invited_accounts_and_transaction_references(self):
        with Session(self.engine) as db:
            db.add_all([User(id=6, name='Invitada', created_by_id=1, login_email='invite@example.com'),
                        User(id=7, name='Pagadora', created_by_id=1)])
            db.add(Expense(group_id=1, payer_id=1, description='Histórico', amount=10,
                           payer_contributions={'1': '5', '7': '5'}, voided=True))
            db.commit()
        for uid in (6, 7):
            self.assertEqual(self.call('owner', 'DELETE', f'/users/{uid}').status_code, 409)
            with Session(self.engine) as db:
                self.assertIsNotNone(db.get(User, uid))

    def test_remove_member_is_owner_only_and_preserves_person_and_other_trips(self):
        path = '/group-members/group/1/people/5'
        with Session(self.engine) as db:
            db.add(GroupMember(group_id=2, user_id=5, role='member'))
            db.commit()
        for actor in ('reader', 'writer', 'outsider'):
            self.assertEqual(self.call(actor, 'DELETE', path).status_code, 403)
        self.assertEqual(self.client.delete(path).status_code, 401)
        self.assertEqual(self.call('owner', 'DELETE', '/group-members/group/1/people/1').status_code, 409)
        for _ in range(2):
            self.assertEqual(self.call('owner', 'DELETE', path).status_code, 200)
        with Session(self.engine) as db:
            self.assertIsNotNone(db.get(User, 5))
            self.assertIsNone(db.query(GroupMember).filter_by(group_id=1, user_id=5).first())
            self.assertIsNotNone(db.query(GroupMember).filter_by(group_id=2, user_id=5).first())
        self.assertEqual(self.call('owner', 'DELETE', '/group-members/group/1/people/3').status_code, 200)
        self.assertEqual(self.call('reader', 'GET', '/groups/1/balances').status_code, 403)

    def test_remove_member_blocks_participants_and_multiple_payers_even_when_voided(self):
        payload = self.expense()
        payload.update(participants=[1, 3], payer_contributions={'1': '6.00', '5': '4.00'})
        result = self.call('owner', 'POST', '/expenses/', payload)
        self.assertEqual(result.status_code, 200, result.text)
        for voided in (False, True):
            if voided:
                self.call('owner', 'POST', f"/expenses/{result.json()['id']}/void")
            for uid in (3, 5):
                response = self.call('owner', 'DELETE', f'/group-members/group/1/people/{uid}')
                self.assertEqual(response.status_code, 409, response.text)
                self.assertEqual(response.json()['detail'], 'Member has trip transactions')

    def test_remove_member_blocks_both_payment_sides_even_when_voided(self):
        payment = self.call('owner', 'POST', '/payments/', dict(
            group_id=1, from_user_id=3, to_user_id=5, amount='2.00',
            payment_date='2026-09-10', request_id=str(uuid4())))
        self.assertEqual(payment.status_code, 200, payment.text)
        for voided in (False, True):
            if voided:
                self.call('owner', 'POST', f"/payments/{payment.json()['id']}/void")
            for uid in (3, 5):
                self.assertEqual(self.call('owner', 'DELETE', f'/group-members/group/1/people/{uid}').status_code, 409)

    def test_extra_expense_id_cannot_redirect_creation_authorization(self):
        own = self.call('writer', 'POST', '/expenses/', self.expense()).json()['id']
        payload = self.expense()
        payload.update(expense_id=own, group_id=2, payer_id=4, participants=[4])
        response = self.call('writer', 'POST', '/expenses/', payload)
        self.assertEqual(response.status_code, 403, response.text)
        with Session(self.engine) as db:
            self.assertEqual(db.query(Expense).filter_by(group_id=2).count(), 0)

    def test_explicit_invitation_links_guest_but_contact_email_does_not(self):
        subject = str(uuid4())
        with Session(self.engine) as db:
            account = resolve_identity(dict(id=subject, email='guest@example.com', user_metadata={}), db)
            self.assertNotEqual(account.id, 5)
        invitation = {'can_register_expenses':True,'login_email':'invited@example.com'}
        self.assertEqual(self.call('owner','PUT','/group-members/group/1/access/5',invitation).status_code,200)
        with Session(self.engine) as db:
            account = resolve_identity(dict(id=str(uuid4()), email='invited@example.com', user_metadata={}), db)
            self.assertEqual(account.id,5)
        self.assertEqual(self.call('owner','PUT','/group-members/group/1/access/5', {**invitation,'login_email':'other@example.com'}).status_code,409)


class TokenVerificationTest(unittest.TestCase):
    def test_missing_configuration_fails_closed(self):
        with patch.dict('os.environ', {'SUPABASE_URL':'','SUPABASE_PUBLISHABLE_KEY':''}):
            with self.assertRaises(HTTPException) as failure:
                verify_token('untrusted')
            self.assertEqual(failure.exception.status_code,503)
