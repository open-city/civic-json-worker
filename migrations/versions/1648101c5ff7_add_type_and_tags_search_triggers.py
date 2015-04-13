"""Updating the project search trigger to include type and tags

Revision ID: 1648101c5ff7
Revises: 5614ac52de37
Create Date: 2015-04-13 12:14:50.726839

"""

# revision identifiers, used by Alembic.
revision = '1648101c5ff7'
down_revision = '5614ac52de37'

from alembic import op

def upgrade():
    droptrigger = "DROP TRIGGER IF EXISTS tsvupdate_projects_trigger ON project"
    createtrigger = "CREATE TRIGGER tsvupdate_projects_trigger BEFORE INSERT OR UPDATE ON project FOR EACH ROW EXECUTE PROCEDURE tsvector_update_trigger(tsv_body, 'pg_catalog.english', name, description, type, categories, tags, github_details, status);"
    op.execute(droptrigger)
    op.execute(createtrigger)


def downgrade():
    droptrigger = "DROP TRIGGER IF EXISTS tsvupdate_projects_trigger ON project"
    createtrigger = "CREATE TRIGGER tsvupdate_projects_trigger BEFORE INSERT OR UPDATE ON project FOR EACH ROW EXECUTE PROCEDURE tsvector_update_trigger(tsv_body, 'pg_catalog.english', name, description, categories, github_details, status);"
    op.execute(droptrigger)
    op.execute(createtrigger)
