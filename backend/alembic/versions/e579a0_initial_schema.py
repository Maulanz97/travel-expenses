"""Initial schema consolidated for fresh installations.

Earlier development revisions require an explicit database reset.
"""
from alembic import op
import sqlalchemy as sa

revision = "e579a0"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('groups',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_groups_id'), 'groups', ['id'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('auth_subject', sa.String(length=36), nullable=True),
    sa.Column('login_email', sa.String(length=320), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('email', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('auth_subject'),
    sa.UniqueConstraint('login_email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_table('expenses',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('expense_date', sa.Date(), nullable=True),
    sa.Column('voided', sa.Boolean(), server_default='0', nullable=False),
    sa.Column('history', sa.JSON(), server_default='[]', nullable=False),
    sa.Column('custom_shares', sa.JSON(), nullable=True),
    sa.Column('payer_contributions', sa.JSON(), nullable=True),
    sa.Column('request_id', sa.String(length=36), nullable=True),
    sa.Column('request_fingerprint', sa.String(length=64), nullable=True),
    sa.Column('payer_id', sa.Integer(), nullable=False),
    sa.Column('group_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['payer_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('request_id')
    )
    op.create_index(op.f('ix_expenses_id'), 'expenses', ['id'], unique=False)
    op.create_table('group_members',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('group_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('can_register_expenses', sa.Boolean(), server_default='0', nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_group_members_id'), 'group_members', ['id'], unique=False)
    op.create_table('payments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('group_id', sa.Integer(), nullable=False),
    sa.Column('from_user_id', sa.Integer(), nullable=False),
    sa.Column('to_user_id', sa.Integer(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=11, scale=2), nullable=False),
    sa.Column('payment_date', sa.Date(), nullable=False),
    sa.Column('request_id', sa.String(length=36), nullable=False),
    sa.Column('voided', sa.Boolean(), server_default='0', nullable=False),
    sa.CheckConstraint('amount > 0', name='payment_positive'),
    sa.CheckConstraint('from_user_id != to_user_id', name='payment_distinct_people'),
    sa.ForeignKeyConstraint(['from_user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['to_user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('request_id')
    )
    op.create_index(op.f('ix_payments_group_id'), 'payments', ['group_id'], unique=False)
    op.create_table('expense_participants',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('expense_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['expense_id'], ['expenses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_expense_participants_id'), 'expense_participants', ['id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_expense_participants_id'), table_name='expense_participants')
    op.drop_table('expense_participants')
    op.drop_index(op.f('ix_payments_group_id'), table_name='payments')
    op.drop_table('payments')
    op.drop_index(op.f('ix_group_members_id'), table_name='group_members')
    op.drop_table('group_members')
    op.drop_index(op.f('ix_expenses_id'), table_name='expenses')
    op.drop_table('expenses')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_groups_id'), table_name='groups')
    op.drop_table('groups')
