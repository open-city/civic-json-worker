""" Add rsvps column to events

Revision ID: 575d8824e34c
Revises: 1440cf6cc91c
Create Date: 2015-08-19 12:01:20.698048

"""

# revision identifiers, used by Alembic.
revision = '575d8824e34c'
down_revision = '1440cf6cc91c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('event', sa.Column('rsvps', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('event', 'rsvps')
