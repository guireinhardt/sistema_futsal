"""Add penalties to matches

Revision ID: c7d2e9f1a3b4
Revises: b58724b58709
Create Date: 2026-11-06 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7d2e9f1a3b4'
down_revision = 'b58724b58709'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.add_column(sa.Column('penalties_a', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('penalties_b', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.drop_column('penalties_b')
        batch_op.drop_column('penalties_a')
