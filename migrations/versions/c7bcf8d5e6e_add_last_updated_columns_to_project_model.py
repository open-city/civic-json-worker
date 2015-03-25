"""empty message

Revision ID: c7bcf8d5e6e
Revises: 2e30a731a0e3
Create Date: 2015-03-25 10:37:18.786185

"""

# revision identifiers, used by Alembic.
revision = 'c7bcf8d5e6e'
down_revision = '2e30a731a0e3'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('project', sa.Column('last_updated_civic_json', sa.Unicode(), nullable=True))
    op.add_column('project', sa.Column('last_updated_root_files', sa.Unicode(), nullable=True))


def downgrade():
    op.drop_column('project', 'last_updated_civic_json')
    op.drop_column('project', 'last_updated_root_files')
