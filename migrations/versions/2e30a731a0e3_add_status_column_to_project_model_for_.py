"""Add status column to Project model for Issue #133

Revision ID: 2e30a731a0e3
Revises: 457b2ba1dfb2
Create Date: 2015-03-09 18:00:01.083339

"""

# revision identifiers, used by Alembic.
revision = '2e30a731a0e3'
down_revision = '457b2ba1dfb2'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('project', sa.Column('status', sa.Unicode(), nullable=True))

def downgrade():
    op.drop_column('project', 'status')
