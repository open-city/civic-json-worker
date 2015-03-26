"""Updating the project search trigger to include the status field.

Revision ID: 4e84bf5dfb0c
Revises: c7bcf8d5e6e
Create Date: 2015-03-26 14:25:18.237948

"""

# revision identifiers, used by Alembic.
revision = '4e84bf5dfb0c'
down_revision = 'c7bcf8d5e6e'

from alembic import op

def upgrade():
    droptrigger = "DROP TRIGGER IF EXISTS tsvupdate_projects_trigger ON project"
    createtrigger = "CREATE TRIGGER tsvupdate_projects_trigger BEFORE INSERT OR UPDATE ON project FOR EACH ROW EXECUTE PROCEDURE tsvector_update_trigger(tsv_body, 'pg_catalog.english', name, description, categories, github_details, status);"
    op.execute(droptrigger)
    op.execute(createtrigger)


def downgrade():
    droptrigger = "DROP TRIGGER IF EXISTS tsvupdate_projects_trigger ON project"
    createtrigger = "CREATE TRIGGER tsvupdate_projects_trigger BEFORE INSERT OR UPDATE ON project FOR EACH ROW EXECUTE PROCEDURE tsvector_update_trigger(tsv_body, 'pg_catalog.english', name, description, categories, github_details);"
    op.execute(droptrigger)
    op.execute(createtrigger)
