"""change expense amount to numeric

Revision ID: 6d43033e01eb
Revises: 
Create Date: 2026-09-03 18:20:30.407632

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d43033e01eb'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("expenses", schema=None) as batch_op:
        batch_op.alter_column(
            "amount",
            existing_type=sa.FLOAT(),
            type_=sa.Numeric(precision=10, scale=2),
            existing_nullable=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("expenses", schema=None) as batch_op:
        batch_op.alter_column(
            "amount",
            existing_type=sa.Numeric(precision=10, scale=2),
            type_=sa.FLOAT(),
            existing_nullable=False
        )
