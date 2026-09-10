"""Explicit local bootstrap: link an existing organizer to a verified login email.

Run before that person signs in for the first time. Does not send email.
"""
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime
from app.database import SessionLocal
from app.models.user import User
from app.models.group_member import GroupMember
from app.schemas.user import UserCreate

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--user-id', required=True, type=int)
    parser.add_argument('--email', required=True)
    args = parser.parse_args()
    email = args.email.strip().lower()
    UserCreate(name='Organizador', email=email)
    with SessionLocal() as db:
        person = db.get(User, args.user_id)
        if not person or not db.query(GroupMember).filter_by(user_id=args.user_id, role='owner').first():
            parser.error('The selected person is not an existing organizer.')
        if person.auth_subject or person.login_email:
            parser.error('This person already has an access link; no changes made.')
        if db.query(User).filter_by(login_email=email).first():
            parser.error('Email already linked; no automatic account merge is allowed.')
        path = Path('expenses.db').resolve()
        backup = path.with_name(f'expenses-{datetime.now():%Y%m%d-%H%M%S}.db.bak')
        with sqlite3.connect(path) as source, sqlite3.connect(backup) as target:
            source.backup(target)
        person.login_email = email
        db.commit()
        print(f'Organizer access prepared. Backup: {backup}')

if __name__ == '__main__':
    main()
