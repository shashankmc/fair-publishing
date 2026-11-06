"""The registry: what was published, pointing to the repository record."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class PublishingBase(DeclarativeBase):
    """The package's own tables. Hosts create them from this metadata or from
    the package's migrations."""


class Publication(PublishingBase):
    __tablename__ = "publications"
    __table_args__ = (UniqueConstraint("owner_id", "kind", "artefact_id", name="uq_publications_artefact"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id: Mapped[str] = mapped_column(String(255), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    artefact_id: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(1000))
    description: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[str] = mapped_column(Text, default="")
    doi: Mapped[str] = mapped_column(String(255))
    record_url: Mapped[str] = mapped_column(String(1000))
    access: Mapped[str] = mapped_column(String(20))
    license: Mapped[str] = mapped_column(String(100))
    related_dataset_doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Naive UTC, as SQLite and most hosts store it.
    published_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    def to_dict(self, owner_id=None):
        return {
            "id": self.id,
            "kind": self.kind,
            "artefact_id": self.artefact_id,
            "title": self.title,
            "doi": self.doi,
            "record_url": self.record_url,
            "access": self.access,
            "license": self.license,
            "related_dataset_doi": self.related_dataset_doi,
            "published_at": self.published_at.isoformat(),
            "mine": owner_id is not None and self.owner_id == owner_id,
        }
