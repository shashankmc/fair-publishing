"""The shipped revision builds the table the model describes."""
import importlib.util
import pathlib

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from fair_publishing.models import Publication

REVISION = pathlib.Path(__file__).parent.parent / "src/fair_publishing/migrations/versions/fp_0001_publications.py"


def _columns(engine):
    return {c["name"]: (str(c["type"]), c["nullable"]) for c in sa.inspect(engine).get_columns("publications")}


def test_the_revision_matches_the_model():
    spec = importlib.util.spec_from_file_location("revision", REVISION)
    revision = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(revision)
    migrated = sa.create_engine("sqlite://")
    with migrated.begin() as connection:
        revision.op = Operations(MigrationContext.configure(connection))
        revision.upgrade()
    modelled = sa.create_engine("sqlite://")
    Publication.metadata.create_all(modelled)

    assert _columns(migrated) == _columns(modelled)
