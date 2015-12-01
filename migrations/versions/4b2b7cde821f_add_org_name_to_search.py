""" Adds organization name to the project search tsv

Revision ID: 4b2b7cde821f
Revises: 15593ff6a15f
Create Date: 2015-11-30 17:21:56.928359

"""

# revision identifiers, used by Alembic.
revision = '4b2b7cde821f'
down_revision = '15593ff6a15f'

from alembic import op
import sqlalchemy as sa


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
             setweight(to_tsvector('pg_catalog.english', coalesce(new.description,'')), 'B') ||
             setweight(to_tsvector('pg_catalog.english', coalesce(new.languages,'')), 'A') ||
             setweight(to_tsvector('pg_catalog.english', coalesce(new.organization_name,'')), 'A');
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
    createtriggerfunc = '''
        CREATE FUNCTION project_search_trigger() RETURNS trigger AS $$
        begin
          new.tsv_body :=
             setweight(to_tsvector('pg_catalog.english', coalesce(new.status,'')), 'A') ||
             setweight(to_tsvector('pg_catalog.english', coalesce(new.tags,'')), 'A') ||
             setweight(to_tsvector('pg_catalog.english', coalesce(new.name,'')), 'B') ||
             setweight(to_tsvector('pg_catalog.english', coalesce(new.description,'')), 'B') ||
             setweight(to_tsvector('pg_catalog.english', coalesce(new.languages,'')), 'A');
          return new;
        end
        $$ LANGUAGE plpgsql;
        '''
    createtrigger = "CREATE TRIGGER tsvupdate_projects_trigger BEFORE INSERT OR UPDATE ON project FOR EACH ROW EXECUTE PROCEDURE project_search_trigger();"
    op.execute(droptrigger)
    op.execute(droptriggerfunc)
    op.execute(createtriggerfunc)
    op.execute(createtrigger)
