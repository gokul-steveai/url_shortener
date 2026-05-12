"""add_role_to_users

Revision ID: 12c528d1f2d8
Revises: ffdbd3ad560e
Create Date: 2026-05-12 14:40:48.560670

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '12c528d1f2d8'
down_revision: Union[str, Sequence[str], None] = 'ffdbd3ad560e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('role', sa.String(length=20), server_default='user', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'role')
