"""Personal invitations scoped to a trip membership."""
from alembic import op
import sqlalchemy as sa

revision = 'f183b1'
down_revision = 'e579a0'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('group_members') as batch:
        batch.add_column(sa.Column('access_user_id', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('invite_hash', sa.String(64), nullable=True))
        batch.add_column(sa.Column('invite_expires', sa.DateTime(), nullable=True))
        batch.create_foreign_key('fk_member_access_user', 'users', ['access_user_id'], ['id'])
        batch.create_unique_constraint('uq_member_invite_hash', ['invite_hash'])
        batch.create_unique_constraint('uq_trip_access_user', ['group_id', 'access_user_id'])

def downgrade():
    with op.batch_alter_table('group_members') as batch:
        batch.drop_constraint('uq_trip_access_user', type_='unique')
        batch.drop_constraint('uq_member_invite_hash', type_='unique')
        batch.drop_constraint('fk_member_access_user', type_='foreignkey')
        batch.drop_column('invite_expires')
        batch.drop_column('invite_hash')
        batch.drop_column('access_user_id')
