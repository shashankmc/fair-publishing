"""What a host supplies: the artefacts to publish and where tokens are kept."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass
class Artefact:
    """A Dataset or Model the user may publish, as the host describes it."""

    kind: str  # "dataset" or "model"
    id: str
    title: str
    description: str = ""
    task_type: Optional[str] = None
    # jurisdiction, language, document_type, ecli; any may be missing.
    legal: dict = field(default_factory=dict)
    # Models only: {"id", "title"} of the Dataset it was trained on.
    training_dataset: Optional[dict] = None
    # Where the labels came from: source counts, models, prompt versions, agreement.
    provenance: dict = field(default_factory=dict)


@dataclass
class DepositFile:
    name: str
    content: bytes


@dataclass
class RoundTrip:
    """Whether the exported files predict what the platform model does."""

    ok: bool
    detail: str = ""


class ArtefactProvider(Protocol):
    def list(self, owner_id: str) -> list[Artefact]: ...

    def get(self, owner_id: str, kind: str, artefact_id: str) -> Optional[Artefact]: ...

    def files(self, owner_id: str, artefact: Artefact) -> list[DepositFile]:
        """The artefact's own files: the data, or the exported model."""

    def verify(self, owner_id: str, artefact: Artefact) -> RoundTrip:
        """For a model, the round-trip check on the holdout. A dataset passes."""


class SecretStore(Protocol):
    def get(self, owner_id: str, name: str) -> Optional[str]: ...

    def set(self, owner_id: str, name: str, value: str) -> None: ...

    def delete(self, owner_id: str, name: str) -> None: ...
