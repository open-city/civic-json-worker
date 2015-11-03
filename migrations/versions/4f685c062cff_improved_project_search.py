""" Much improved project search.

Revision ID: 4f685c062cff
Revises: 8081a5906af
Create Date: 2015-09-15 21:53:02.468239

"""

# revision identifiers, used by Alembic.
revision = '4f685c062cff'
down_revision = '8081a5906af'

from alembic import op

def upgrade():
    droptrigger = "DROP TRIGGER IF EXISTS tsvupdate_projects_trigger ON project"
    droptriggerfunc = "DROP FUNCTION IF EXISTS project_search_trigger()"
    createtriggerfunc = '''
        CREATE FUNCTION project_search_trigger() RETURNS trigger AS $$
        begin
          new.tsv_body :=
             setweight(to_tsvector('pg_catalog.english', coalesce(new.status,'')), 'A') ||
             setweight(to_tsvector('pg_catalog.english', coalesce(new.tags,'')), 'A') ||
             setweight(to_tsvector('pg_catalog.english', coalesce(new.name,'')), 'B') ||
             setweight(to_tsvector('pg_catalog.english', coalesce(new.description,'')), 'B');
          return new;
        end
        $$ LANGUAGE plpgsql;
        '''
    createtrigger = "CREATE TRIGGER tsvupdate_projects_trigger BEFORE INSERT OR UPDATE ON project FOR EACH ROW EXECUTE PROCEDURE project_search_trigger();"
    op.execute(droptrigger)
    op.execute(droptriggerfunc)
    op.execute(createtriggerfunc)
    op.execute(createtrigger)


def downgrade():
    droptrigger = "DROP TRIGGER IF EXISTS tsvupdate_projects_trigger ON project"
    droptriggerfunc = "DROP FUNCTION IF EXISTS project_search_trigger()"
    createtrigger = "CREATE TRIGGER tsvupdate_projects_trigger BEFORE INSERT OR UPDATE ON project FOR EACH ROW EXECUTE PROCEDURE tsvector_update_trigger(tsv_body, 'pg_catalog.english', name, description, type, categories, tags, github_details, status);"
    op.execute(droptrigger)
    op.execute(droptriggerfunc)
    op.execute(createtrigger)
