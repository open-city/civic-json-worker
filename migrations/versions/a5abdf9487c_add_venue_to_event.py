from alembic import op
import sqlalchemy as sa


"""Add Venue To Event

Revision ID: a5abdf9487c
Revises: 578ce9f8d1
Create Date: 2018-01-12 16:43:53.741499

"""

# revision identifiers, used by Alembic.
revision = 'a5abdf9487c'
down_revision = '578ce9f8d1'


def upgrade():
    op.add_column('event', sa.Column('lat', sa.types.DECIMAL(20, 17)))
    op.add_column('event', sa.Column('lon', sa.types.DECIMAL(20, 17)))


def downgrade():
    op.drop_column('event', 'lat')
    op.drop_column('event', 'lon')
