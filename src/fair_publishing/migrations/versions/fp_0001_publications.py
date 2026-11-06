"""The publications registry.

Owned by the package. A host that runs Alembic adds this directory to its
``version_locations``; the branch label keeps it apart from the host's chain.
"""
import sqlalchemy as sa
from alembic import op

revision = "fp_0001_publications"
down_revision = None
branch_labels = ("fair_publishing",)
depends_on = None


def upgrade():
    op.create_table(
        "publications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("owner_id", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("artefact_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=1000), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("keywords", sa.Text(), nullable=False),
        sa.Column("doi", sa.String(length=255), nullable=False),
        sa.Column("record_url", sa.String(length=1000), nullable=False),
        sa.Column("access", sa.String(length=20), nullable=False),
        sa.Column("license", sa.String(length=100), nullable=False),
        sa.Column("related_dataset_doi", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("owner_id", "kind", "artefact_id", name="uq_publications_artefact"),
    )
    op.create_index("ix_publications_owner_id", "publications", ["owner_id"])


def downgrade():
    op.drop_index("ix_publications_owner_id", table_name="publications")
    op.drop_table("publications")
