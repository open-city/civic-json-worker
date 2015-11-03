""" Added id column to organization

Revision ID: 532c3f11a51b
Revises: 1648101c5ff7
Create Date: 2015-07-21 11:10:36.752010

"""

# revision identifiers, used by Alembic.
revision = '532c3f11a51b'
down_revision = '1648101c5ff7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('organization', sa.Column('id', sa.Unicode()))


def downgrade():
    op.drop_column('organization', 'id')
