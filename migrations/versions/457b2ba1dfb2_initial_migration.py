"""initial migration

Revision ID: 457b2ba1dfb2
Revises: None
Create Date: 2015-11-02 14:10:08.014600

"""

# revision identifiers, used by Alembic.
revision = '457b2ba1dfb2'
down_revision = None

from alembic import op
import sqlalchemy as sa
from models import JsonType, TSVectorType

def upgrade():
    op.create_table(
        'organization',
        sa.Column('name', sa.Unicode(), nullable=False),
        sa.Column('website', sa.Unicode(), nullable=True),
        sa.Column('events_url', sa.Unicode(), nullable=True),
        sa.Column('rss', sa.Unicode(), nullable=True),
        sa.Column('projects_list_url', sa.Unicode(), nullable=True),
        sa.Column('type', sa.Unicode(), nullable=True),
        sa.Column('city', sa.Unicode(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('last_updated', sa.Integer(), nullable=True),
        sa.Column('started_on', sa.Unicode(), nullable=True),
        sa.Column('keep', sa.Boolean(), nullable=True),
        sa.Column('tsv_body', TSVectorType(), nullable=True),
        sa.PrimaryKeyConstraint('name')
    )
    op.create_index('index_org_tsv_body', 'organization', ['tsv_body'], unique=False, postgresql_using='gin')

    op.create_table(
        'error',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('error', sa.Unicode(), nullable=True),
        sa.Column('time', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'story',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.Unicode(), nullable=True),
        sa.Column('link', sa.Unicode(), nullable=True),
        sa.Column('type', sa.Unicode(), nullable=True),
        sa.Column('keep', sa.Boolean(), nullable=True),
        sa.Column('organization_name', sa.Unicode(), nullable=False),
        sa.ForeignKeyConstraint(['organization_name'], ['organization.name'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'project',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Unicode(), nullable=True),
        sa.Column('code_url', sa.Unicode(), nullable=True),
        sa.Column('link_url', sa.Unicode(), nullable=True),
        sa.Column('description', sa.Unicode(), nullable=True),
        sa.Column('type', sa.Unicode(), nullable=True),
        sa.Column('categories', sa.Unicode(), nullable=True),
        sa.Column('github_details', JsonType(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.Column('last_updated_issues', sa.Unicode(), nullable=True),
        sa.Column('keep', sa.Boolean(), nullable=True),
        sa.Column('tsv_body', TSVectorType(), nullable=True),
        sa.Column('organization_name', sa.Unicode(), nullable=False),
        sa.ForeignKeyConstraint(['organization_name'], ['organization.name'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('index_project_tsv_body', 'project', ['tsv_body'], unique=False, postgresql_using='gin')

    op.create_table(
        'event',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Unicode(), nullable=True),
        sa.Column('description', sa.Unicode(), nullable=True),
        sa.Column('event_url', sa.Unicode(), nullable=True),
        sa.Column('location', sa.Unicode(), nullable=True),
        sa.Column('created_at', sa.Unicode(), nullable=True),
        sa.Column('start_time_notz', sa.DateTime(), nullable=True),
        sa.Column('end_time_notz', sa.DateTime(), nullable=True),
        sa.Column('utc_offset', sa.Integer(), nullable=True),
        sa.Column('keep', sa.Boolean(), nullable=True),
        sa.Column('organization_name', sa.Unicode(), nullable=False),
        sa.ForeignKeyConstraint(['organization_name'], ['organization.name'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'issue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.Unicode(), nullable=True),
        sa.Column('html_url', sa.Unicode(), nullable=True),
        sa.Column('body', sa.Unicode(), nullable=True),
        sa.Column('keep', sa.Boolean(), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_issue_project_id', 'issue', ['project_id'], unique=False)

    op.create_table(
        'label',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Unicode(), nullable=True),
        sa.Column('color', sa.Unicode(), nullable=True),
        sa.Column('url', sa.Unicode(), nullable=True),
        sa.Column('issue_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['issue_id'], ['issue.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_label_issue_id', 'label', ['issue_id'], unique=False)


def downgrade():
    op.drop_index('ix_label_issue_id', table_name='label')
    op.drop_table('label')
    op.drop_index('ix_issue_project_id', table_name='issue')
    op.drop_table('issue')
    op.drop_table('event')
    op.drop_index('index_project_tsv_body', table_name='project')
    op.drop_table('project')
    op.drop_table('story')
    op.drop_table('error')
    op.drop_index('index_org_tsv_body', table_name='organization')
    op.drop_table('organization')
