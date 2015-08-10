Database migration scripts with Alembic.

To make changes to the database, first modify the schema. Then run the
following command to autogenerate a migration script:

    alembic revision --autogenerate -m "Migration description."

This command must be run from this directory (the directory containing
alembic.ini).

You can run migrations like this:

    alembic upgrade head

Or you can print the SQL that is generated like this:

    alembic upgrade head --sql
