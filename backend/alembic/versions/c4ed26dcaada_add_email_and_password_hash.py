"""add email and password hash

Revision ID: c4ed26dcaada
Revises: f020244c1424
Create Date: 2026-10-07 10:42:14.437182

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4ed26dcaada'
down_revision: Union[str, Sequence[str], None] = 'f020244c1424'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('email', sa.String(length=255), nullable=False))
    op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=False))
    op.create_unique_constraint('uq_users_email', 'users', ['email'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_column('users', 'password_hash')
    op.drop_column('users', 'email')
