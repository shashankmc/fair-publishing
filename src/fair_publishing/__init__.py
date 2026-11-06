"""Publish datasets and models to a research repository with FAIR metadata."""
from dataclasses import dataclass
from typing import Callable, Optional

from .protocols import Artefact, ArtefactProvider, DepositFile, RoundTrip, SecretStore

__version__ = "0.1.0"

__all__ = ["Artefact", "ArtefactProvider", "DepositFile", "RoundTrip", "SecretStore", "init_publishing"]


@dataclass
class _Host:
    db: object
    artefact_provider: ArtefactProvider
    secret_store: SecretStore
    login_required: Callable
    current_owner: Callable[[], str]
    feature_gate: Callable[[str], bool]
    card_drafter: Optional[Callable]


def init_publishing(
    app,
    *,
    db,
    artefact_provider,
    secret_store,
    login_required,
    current_owner,
    feature_gate=None,
    card_drafter=None,
    url_prefix="/api/publishing",
):
    """Mount the publishing API on a host Flask app.

    ``db`` is the host's Flask-SQLAlchemy handle; the registry table comes from
    ``fair_publishing.models.PublishingBase.metadata``. ``login_required`` is the
    host's sign-in decorator, applied to every route, and ``current_owner``
    returns the signed-in user's id. ``feature_gate(owner_id)`` turns publishing
    off for a user (on by default). ``card_drafter(artefact)`` may return a card
    draft, for instance from an LLM; the user approves it before it is used.
    """
    from .routes import publishing_bp

    app.extensions["fair_publishing"] = _Host(
        db=db,
        artefact_provider=artefact_provider,
        secret_store=secret_store,
        login_required=login_required,
        current_owner=current_owner,
        feature_gate=feature_gate or (lambda owner_id: True),
        card_drafter=card_drafter,
    )
    app.register_blueprint(publishing_bp, url_prefix=url_prefix)
