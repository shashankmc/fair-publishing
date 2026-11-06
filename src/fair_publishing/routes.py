"""The HTTP API, under /api/publishing (docs/openapi.yaml)."""
import json

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import or_

from . import cards, config
from . import metadata as metadata_module
from .models import Publication
from .protocols import DepositFile
from .zenodo import RepositoryError, Zenodo

TOKEN_NAME = "zenodo_token"

publishing_bp = Blueprint("fair_publishing", __name__)


class ApiError(Exception):
    def __init__(self, status, message, code, **extra):
        super().__init__(message)
        self.status = status
        self.body = {"error": message, "code": code, **extra}


@publishing_bp.errorhandler(ApiError)
def _api_error(error):
    return jsonify(error.body), error.status


def _host():
    return current_app.extensions["fair_publishing"]


def _owner():
    return str(_host().current_owner())


def _enabled(owner_id):
    return bool(_host().feature_gate(owner_id))


@publishing_bp.before_request
def _sign_in():
    """The host's sign-in decorator, around nothing: a refusal it returns or
    raises ends the request before any route runs."""
    return _host().login_required(lambda: None)()


def _require_enabled():
    if not _enabled(_owner()):
        raise ApiError(403, "Publishing is turned off on this platform.", "publishing_disabled")


@publishing_bp.route("/config", methods=["GET"])
def get_config():
    url = config.zenodo_url()
    return jsonify(
        {
            "enabled": _enabled(_owner()),
            "repository": {
                "id": "zenodo",
                "name": "Zenodo",
                "sandbox": "sandbox." in url,
                "token_url": f"{url}/account/settings/applications/tokens/new/",
            },
            "community": config.community(),
            "licenses": config.licenses(),
            "required_fields": config.required_fields(),
            "access_levels": config.ACCESS_LEVELS,
        }
    )


def _session():
    return _host().db.session


def _publication_of(owner_id, kind, artefact_id):
    return _session().query(Publication).filter_by(owner_id=owner_id, kind=kind, artefact_id=artefact_id).first()


def _artefact_dict(owner_id, artefact):
    publication = _publication_of(owner_id, artefact.kind, artefact.id)
    body = {
        "kind": artefact.kind,
        "id": artefact.id,
        "title": artefact.title,
        "description": artefact.description,
        "task_type": artefact.task_type,
        "legal": artefact.legal,
        "training_dataset": None,
        "publication": publication.to_dict(owner_id) if publication else None,
    }
    if artefact.training_dataset:
        dataset = _publication_of(owner_id, "dataset", artefact.training_dataset["id"])
        body["training_dataset"] = {**artefact.training_dataset, "doi": dataset.doi if dataset else None}
    return body


@publishing_bp.route("/token", methods=["GET"])
def token_status():
    _require_enabled()
    return jsonify({"connected": bool(_host().secret_store.get(_owner(), TOKEN_NAME))})


@publishing_bp.route("/token", methods=["PUT"])
def save_token():
    _require_enabled()
    token = str((request.get_json(silent=True) or {}).get("token") or "").strip()
    if not token:
        raise ApiError(400, "Paste your personal access token.", "token_missing")
    _host().secret_store.set(_owner(), TOKEN_NAME, token)
    return jsonify({"connected": True})


@publishing_bp.route("/token", methods=["DELETE"])
def delete_token():
    _require_enabled()
    _host().secret_store.delete(_owner(), TOKEN_NAME)
    return "", 204


@publishing_bp.route("/artefacts", methods=["GET"])
def list_artefacts():
    _require_enabled()
    owner_id = _owner()
    artefacts = _host().artefact_provider.list(owner_id)
    return jsonify({"artefacts": [_artefact_dict(owner_id, artefact) for artefact in artefacts]})


ATTESTATIONS = {
    "license": "You may release it under the chosen license.",
    "rights": "You hold the rights to its content.",
    "personal_data": "It contains no personal data that may not be published.",
}


def _artefact(owner_id, body):
    kind, artefact_id = body.get("kind"), str(body.get("id") or "")
    artefact = _host().artefact_provider.get(owner_id, kind, artefact_id) if kind in ("dataset", "model") else None
    if artefact is None:
        raise ApiError(404, "There is nothing of yours to publish with that name.", "not_found")
    return artefact


def _missing_fields(metadata, artefact):
    legal = metadata_module.legal_fields(artefact, metadata)
    missing = []
    for name in config.required_fields():
        value = legal.get(name) if name in metadata_module.LEGAL_FIELDS else metadata.get(name)
        if name == "creators":
            value = [creator for creator in value or [] if str(creator.get("name") or "").strip()]
        if not value or (isinstance(value, str) and not value.strip()):
            missing.append(name)
    return missing


def _checked(owner_id, body, artefact):
    """Everything both preview and publish check. Returns (metadata, related_doi)."""
    metadata = body.get("metadata") or {}
    missing = _missing_fields(metadata, artefact)
    if missing:
        raise ApiError(400, "Fill in: " + ", ".join(name.replace("_", " ") for name in missing) + ".", "missing_fields", missing=missing)
    if metadata.get("license") not in [lic["id"] for lic in config.licenses()]:
        raise ApiError(400, "Choose one of the licenses this platform offers.", "invalid_license")
    access = body.get("access")
    if access not in config.ACCESS_LEVELS:
        raise ApiError(400, "Choose open, restricted or metadata-only access.", "invalid_access")
    if access == "restricted" and not str(body.get("access_conditions") or "").strip():
        raise ApiError(400, "Say who may get the files, and how, for restricted access.", "access_conditions_required")
    card = body.get("card") or {}
    if not str(card.get("text") or "").strip() or card.get("approved") is not True:
        raise ApiError(400, "Read the card and approve it before publishing.", "card_not_approved")

    related_doi = None
    if artefact.kind == "model":
        dataset = artefact.training_dataset or {}
        published = _publication_of(owner_id, "dataset", dataset.get("id")) if dataset.get("id") else None
        if published is None:
            raise ApiError(
                409,
                "Publish the Dataset this Model was trained on first, so the Model can point to it.",
                "dataset_doi_required",
                training_dataset=dataset or None,
            )
        related_doi = published.doi
    if _publication_of(owner_id, artefact.kind, artefact.id):
        raise ApiError(409, "This is already published. Its DOI is in the registry.", "already_published")
    return metadata, related_doi


def _round_trip(owner_id, artefact):
    check = _host().artefact_provider.verify(owner_id, artefact)
    if not check.ok:
        raise ApiError(
            422,
            "The exported Model does not predict what the Model on the platform does, so it is not published.",
            "round_trip_failed",
            detail=check.detail,
        )


def _deposit_files(owner_id, artefact, body, metadata, related_doi):
    """The artefact's own files (none for metadata-only), then what describes them."""
    own = [] if body["access"] == "metadata_only" else _host().artefact_provider.files(owner_id, artefact)
    card = DepositFile(metadata_module.card_name(artefact.kind), body["card"]["text"].encode())
    provenance = DepositFile("provenance.json", _json(artefact.provenance))
    datacite = DepositFile("datacite.json", _json(metadata_module.datacite(artefact, metadata, related_doi)))
    described = [*own, card, provenance, datacite]
    crate = metadata_module.ro_crate(artefact, metadata, described, related_doi)
    return [*described, DepositFile("ro-crate-metadata.json", _json(crate))], crate


def _json(value):
    return json.dumps(value, indent=2, ensure_ascii=False).encode()


@publishing_bp.route("/card-draft", methods=["POST"])
def card_draft():
    _require_enabled()
    owner_id = _owner()
    artefact = _artefact(owner_id, request.get_json(silent=True) or {})
    drafter = _host().card_drafter
    if drafter is not None:
        drafted = drafter(artefact)
        if drafted:
            return jsonify({"card": drafted, "source": "llm"})
    return jsonify({"card": cards.template(artefact), "source": "template"})


@publishing_bp.route("/preview", methods=["POST"])
def preview():
    _require_enabled()
    owner_id = _owner()
    body = request.get_json(silent=True) or {}
    artefact = _artefact(owner_id, body)
    metadata, related_doi = _checked(owner_id, body, artefact)
    if artefact.kind == "model":
        _round_trip(owner_id, artefact)
    files, crate = _deposit_files(owner_id, artefact, body, metadata, related_doi)
    return jsonify(
        {
            "datacite": metadata_module.datacite(artefact, metadata, related_doi),
            "ro_crate": crate,
            "card": body["card"]["text"],
            "files": [{"name": file.name, "size": len(file.content)} for file in files],
        }
    )


@publishing_bp.route("/publish", methods=["POST"])
def publish():
    _require_enabled()
    owner_id = _owner()
    body = request.get_json(silent=True) or {}
    artefact = _artefact(owner_id, body)
    metadata, related_doi = _checked(owner_id, body, artefact)
    attestation = body.get("attestation") or {}
    missing = [name for name in ATTESTATIONS if attestation.get(name) is not True]
    if missing:
        raise ApiError(
            400,
            "Confirm each statement before publishing. A DOI cannot be withdrawn.",
            "attestation_required",
            missing=missing,
        )
    token = _host().secret_store.get(owner_id, TOKEN_NAME)
    if not token:
        raise ApiError(403, "Connect your Zenodo account with a personal access token first.", "token_required")
    if artefact.kind == "model":
        _round_trip(owner_id, artefact)

    files, _ = _deposit_files(owner_id, artefact, body, metadata, related_doi)
    repository_metadata = metadata_module.zenodo_metadata(
        artefact, metadata, body["access"], body.get("access_conditions"), related_doi, config.community()
    )
    try:
        record = Zenodo(config.zenodo_url(), token).deposit(repository_metadata, files)
    except RepositoryError as exc:
        current_app.logger.warning("deposit for %s %s failed: %s", artefact.kind, artefact.id, exc)
        raise ApiError(502, f"{exc}. Nothing was published; try again later.", "repository_failed")

    publication = Publication(
        owner_id=owner_id,
        kind=artefact.kind,
        artefact_id=artefact.id,
        title=metadata["title"],
        description=metadata.get("description") or "",
        keywords=" ".join(metadata.get("keywords") or []),
        doi=record["doi"],
        record_url=record["record_url"],
        access=body["access"],
        license=metadata["license"],
        related_dataset_doi=related_doi,
    )
    _session().add(publication)
    _session().commit()
    return jsonify({"publication": publication.to_dict(owner_id)}), 201


@publishing_bp.route("/registry", methods=["GET"])
def registry():
    _require_enabled()
    owner_id = _owner()
    query = _session().query(Publication)
    kind = request.args.get("kind")
    if kind in ("dataset", "model"):
        query = query.filter(Publication.kind == kind)
    search = (request.args.get("q") or "").strip()
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(Publication.title.ilike(pattern), Publication.description.ilike(pattern), Publication.keywords.ilike(pattern))
        )
    publications = query.order_by(Publication.published_at.desc()).all()
    return jsonify({"publications": [publication.to_dict(owner_id) for publication in publications]})


@publishing_bp.route("/registry/<publication_id>", methods=["GET"])
def registry_entry(publication_id):
    _require_enabled()
    publication = _session().get(Publication, publication_id)
    if publication is None:
        raise ApiError(404, "There is no such publication.", "not_found")
    return jsonify({"publication": publication.to_dict(_owner())})
