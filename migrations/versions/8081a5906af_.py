"""empty message

Revision ID: 8081a5906af
Revises: 575d8824e34c
Create Date: 2015-08-25 18:04:56.738898

"""

# revision identifiers, used by Alembic.
revision = '8081a5906af'
down_revision = '575d8824e34c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('organization', sa.Column('member_count', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('organization', 'member_count')
