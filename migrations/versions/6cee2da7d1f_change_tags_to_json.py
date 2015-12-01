""" Changes tags column type to json

Revision ID: 6cee2da7d1f
Revises: 4b2b7cde821f
Create Date: 2015-12-01 11:13:34.873061

"""

# revision identifiers, used by Alembic.
revision = '6cee2da7d1f'
down_revision = '4b2b7cde821f'

from alembic import op
import sqlalchemy as sa
from models import JsonType


def upgrade():
    op.drop_column('project', 'tags')
    op.add_column('project', sa.Column('tags', JsonType, nullable=True))


def downgrade():
    op.drop_column('project', 'tags')
    op.add_column('project', sa.Column('tags', sa.Unicode(), nullable=True))
