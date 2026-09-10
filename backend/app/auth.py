"""Fail-closed authentication and route authorization for the existing API."""
import json
import os
import secrets
from uuid import UUID
from urllib.request import Request as URLRequest, urlopen
from urllib.error import HTTPError, URLError
from fastapi import Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.group_member import GroupMember
from app.models.expense import Expense
from app.models.payment import Payment


def verify_token(token):
    url = os.getenv('SUPABASE_URL', '').rstrip('/')
    key = os.getenv('SUPABASE_PUBLISHABLE_KEY', '')
    if not url.startswith('https://') or not key:
        raise HTTPException(503, 'Authentication is not configured')
    try:
        request = URLRequest(url + '/auth/v1/user', headers={'apikey': key, 'Authorization': 'Bearer ' + token})
        with urlopen(request, timeout=10) as response:
            identity = json.load(response)
        UUID(identity['id'])
        if not identity.get('email_confirmed_at') or not identity.get('email') or identity.get('is_anonymous'):
            raise HTTPException(401, 'Verified email required')
        return identity
    except HTTPError as error:
        raise HTTPException(401 if error.code in (400, 401, 403) else 503, 'Session could not be verified') from None
    except (URLError, TimeoutError, ValueError, KeyError):
        raise HTTPException(503, 'Authentication unavailable') from None


def resolve_identity(identity, db):
    subject = identity['id']
    user = db.query(User).filter_by(auth_subject=subject).first()
    if user:
        return user
    email = identity['email'].strip().lower()
    # Only an explicit access invitation can link a legacy participant, never contact email.
    user = db.query(User).filter_by(login_email=email).first()
    if user and user.auth_subject:
        raise HTTPException(409, 'Account already linked')
    if not user:
        name = str((identity.get('user_metadata') or {}).get('full_name') or email.split('@')[0])[:100]
        user = User(name=name, email=None, login_email=email)
        db.add(user)
        user.auth_subject = subject
    else:
        claimed = db.query(User).filter(User.id == user.id, User.auth_subject.is_(None), User.login_email == email).update({'auth_subject': subject}, synchronize_session='fetch')
        if not claimed:
            db.rollback()
            raise HTTPException(409, 'Account already linked')
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        user = db.query(User).filter_by(auth_subject=subject).first()
        if not user:
            raise HTTPException(409, 'Account already linked') from None
    return user


def visible_group_ids(db, actor):
    return db.query(GroupMember.group_id).filter_by(user_id=actor.id)


def visible_users(db, actor):
    member_ids = db.query(GroupMember.user_id).filter(GroupMember.group_id.in_(visible_group_ids(db, actor)))
    return db.query(User).filter(or_(User.id == actor.id, User.id.in_(member_ids), User.created_by_id == actor.id))


def membership(db, actor, group_id):
    result = db.query(GroupMember).filter_by(group_id=group_id, user_id=actor.id).first()
    if not result:
        raise HTTPException(403, 'Not a member of this trip')
    return result


def require_owner(db, actor, group_id):
    if membership(db, actor, group_id).role != 'owner':
        raise HTTPException(403, 'Organizer permission required')


def can_manage_person(db, actor, person):
    if not person or person.auth_subject:
        return False
    groups = db.query(GroupMember).filter_by(user_id=person.id).all()
    if not groups:
        return person.created_by_id == actor.id
    owned = {m.group_id for m in db.query(GroupMember).filter_by(user_id=actor.id, role='owner')}
    return all(m.group_id in owned and m.role != 'owner' for m in groups)


async def authorize(request: Request, db: Session = Depends(get_db)):
    if local_development_request(request):
        if '/access/' in request.scope['route'].path:
            raise HTTPException(403, 'Account permissions require authentication')
        db.info['local_development'] = True
        return
    header = request.headers.get('Authorization', '')
    if not header.startswith('Bearer ') or len(header) > 16384:
        raise HTTPException(401, 'Sign in required')
    identity = await run_in_threadpool(verify_token, header[7:])
    actor = resolve_identity(identity, db)
    db.info['actor'] = actor
    route = request.scope['route'].path
    method = request.method
    params = request.path_params
    write = method != 'GET'
    body = {}
    if write:
        try:
            raw = await request.body()
            body = json.loads(raw) if raw else {}
            if not isinstance(body, dict):
                raise ValueError()
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(422, 'Invalid request') from None
    def positive(value):
        try:
            number = int(value)
            if number <= 0:
                raise ValueError()
            return number
        except (TypeError, ValueError):
            raise HTTPException(422, 'Invalid identifier') from None

    if route == '/auth/me':
        return
    if route.startswith('/users'):
        if 'user_id' not in params:
            if method in ('GET', 'POST'):
                return
        target = visible_users(db, actor).filter(User.id == positive(params.get('user_id'))).first()
        if not target:
            raise HTTPException(403, 'Person unavailable')
        if method == 'GET':
            return
        if method == 'PUT' and can_manage_person(db, actor, target):
            return
        raise HTTPException(403, 'Person cannot be changed')
    if route == '/groups/':
        if method in ('GET', 'POST'):
            return
    if route.startswith('/groups/') or route.startswith('/group-members'):
        gid = positive(params.get('group_id') or body.get('group_id'))
        membership(db, actor, gid)
        if write:
            require_owner(db, actor, gid)
            if route == '/group-members/':
                target = visible_users(db, actor).filter(User.id == positive(body.get('user_id'))).first()
                if not target or body.get('role') != 'member':
                    raise HTTPException(403, 'Cannot add this person or role')
        return
    if route.startswith('/expenses') or route.startswith('/expense-participants'):
        # Creation is authorized against its target trip, never an extra expense_id
        # that the creation schema ignores. Only the participant route accepts it.
        eid = params.get('expense_id')
        if route == '/expense-participants/' and method == 'POST':
            eid = body.get('expense_id')
        expense = db.get(Expense, positive(eid)) if eid else None
        if eid and not expense:
            raise HTTPException(404, 'Expense not found')
        if route == '/expenses/' and method == 'GET':
            return  # collection is filtered in the route
        gid = expense.group_id if expense else positive(body.get('group_id'))
        member = membership(db, actor, gid)
        if write and member.role != 'owner':
            if not member.can_register_expenses or (expense and expense.created_by_id != actor.id):
                raise HTTPException(403, 'Expense permission required')
        if method == 'POST' and route == '/expenses/' and body.get('request_id'):
            existing = db.query(Expense).filter_by(request_id=str(body['request_id'])).first()
            if existing and (existing.group_id != gid or (existing.created_by_id != actor.id and not (existing.created_by_id is None and member.role == 'owner'))):
                raise HTTPException(409, 'Request belongs to another operation')
        return
    if route.startswith('/payments'):
        payment = db.get(Payment, positive(params['payment_id'])) if 'payment_id' in params else None
        if 'payment_id' in params and not payment:
            raise HTTPException(404, 'Payment not found')
        gid = payment.group_id if payment else positive(params.get('group_id') or body.get('group_id'))
        membership(db, actor, gid)
        if write:
            require_owner(db, actor, gid)
            if body.get('request_id'):
                existing = db.query(Payment).filter_by(request_id=str(body['request_id'])).first()
                if existing and existing.group_id != gid:
                    raise HTTPException(409, 'Request belongs to another operation')
        return
    raise HTTPException(403, 'Operation not authorized')


def local_development_request(request):
    """Only the explicitly launched loopback Vite proxy knows this ephemeral token."""
    token = os.getenv('LOCAL_DEV_TOKEN', '')
    if os.getenv('APP_ENV') != 'development' or os.getenv('LOCAL_DEV_AUTH') != '1' or len(token) < 32:
        return False
    loopback = {'127.0.0.1', 'localhost', '::1'}
    if not request.client or request.client.host not in loopback or request.url.hostname not in loopback:
        return False
    origin = request.headers.get('origin')
    port = os.getenv('LOCAL_DEV_PORT', '5173')
    if origin and origin not in {f'http://localhost:{port}', f'http://127.0.0.1:{port}'}:
        return False
    return secrets.compare_digest(request.headers.get('x-local-dev-token', ''), token)
