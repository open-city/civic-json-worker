""" Add language column to projects

Revision ID: 219963bb18dc
Revises: 4f685c062cff
Create Date: 2015-09-21 18:06:53.922781

"""

# revision identifiers, used by Alembic.
revision = '219963bb18dc'
down_revision = '4f685c062cff'

from alembic import op
import sqlalchemy as sa
from app import JsonType


def upgrade():
    op.add_column('project', sa.Column('languages', JsonType, nullable=True))

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
             setweight(to_tsvector('pg_catalog.english', coalesce(new.languages,'')), 'B');
          return new;
        end
        $$ LANGUAGE plpgsql;
        '''
    createtrigger = "CREATE TRIGGER tsvupdate_projects_trigger BEFORE INSERT OR UPDATE ON project FOR EACH ROW EXECUTE PROCEDURE project_search_trigger();"
    op.execute(droptrigger)
    op.execute(droptriggerfunc)
    op.execute(createtriggerfunc)
    op.execute(createtrigger)
    ### end Alembic commands ###


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

    op.drop_column('project', 'languages')
