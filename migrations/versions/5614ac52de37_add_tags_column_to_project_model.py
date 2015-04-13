"""empty message

Revision ID: 5614ac52de37
Revises: 4e84bf5dfb0c
Create Date: 2015-04-07 17:01:55.475777

"""

# revision identifiers, used by Alembic.
revision = '5614ac52de37'
down_revision = '4e84bf5dfb0c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('project', sa.Column('tags', sa.Unicode(), nullable=True))


def downgrade():
    op.drop_column('project', 'tags')
