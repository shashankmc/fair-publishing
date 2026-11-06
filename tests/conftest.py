"""A minimal host: sign-in by an X-User header, a fake artefact provider and
secret store, and Zenodo faked at its HTTP boundary."""
import functools
import json

import pytest
from flask import Flask, abort, g, request
from flask_sqlalchemy import SQLAlchemy

from fair_publishing import Artefact, DepositFile, RoundTrip, init_publishing
from fair_publishing.models import PublishingBase


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        user = request.headers.get("X-User")
        if not user:
            abort(401)
        g.user = user
        return view(*args, **kwargs)

    return wrapped


class FakeProvider:
    """Artefacts by (owner, kind, id); `round_trip` is what verify answers."""

    def __init__(self):
        self.artefacts = {}
        self.round_trip = RoundTrip(ok=True, detail="Predictions match on 20 held-back items.")

    def add(self, owner, artefact):
        self.artefacts[(owner, artefact.kind, artefact.id)] = artefact
        return artefact

    def list(self, owner_id):
        return [a for (owner, _, _), a in self.artefacts.items() if owner == owner_id]

    def get(self, owner_id, kind, artefact_id):
        return self.artefacts.get((owner_id, kind, artefact_id))

    def files(self, owner_id, artefact):
        if artefact.kind == "model":
            return [DepositFile("model.skops", b"skops-bytes"), DepositFile("preprocessing.json", b"{}")]
        return [DepositFile("data.csv", b"text,label\nclause,obligation\n")]

    def verify(self, owner_id, artefact):
        return self.round_trip


class MemorySecrets:
    def __init__(self):
        self.values = {}

    def get(self, owner_id, name):
        return self.values.get((owner_id, name))

    def set(self, owner_id, name, value):
        self.values[(owner_id, name)] = value

    def delete(self, owner_id, name):
        self.values.pop((owner_id, name), None)


class FakeZenodo:
    """Stands in for requests.post/put/get, answering like Zenodo's deposit API."""

    def __init__(self):
        self.calls = []
        self.fail = False
        self.next_id = 100

    def _respond(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        if self.fail:
            return FakeResponse(500, {"message": "Internal error"})
        if method == "POST" and url.endswith("/api/deposit/depositions"):
            self.next_id += 1
            return FakeResponse(201, {"id": self.next_id, "links": {"bucket": f"https://zenodo.test/api/files/bucket-{self.next_id}"}})
        if method == "PUT" and "/api/files/" in url:
            return FakeResponse(201, {"key": url.rsplit("/", 1)[-1]})
        if method == "PUT" and "/api/deposit/depositions/" in url:
            return FakeResponse(200, {"id": int(url.rsplit("/", 1)[-1])})
        if method == "POST" and url.endswith("/actions/publish"):
            record = int(url.split("/")[-3])
            return FakeResponse(202, {"id": record, "doi": f"10.5072/zenodo.{record}", "links": {"record_html": f"https://zenodo.test/records/{record}"}})
        return FakeResponse(404, {"message": "Not found"})

    def post(self, url, **kwargs):
        return self._respond("POST", url, **kwargs)

    def put(self, url, **kwargs):
        return self._respond("PUT", url, **kwargs)

    def of(self, method, fragment):
        return [c for c in self.calls if c["method"] == method and fragment in c["url"]]


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body)

    def json(self):
        return self._body


@pytest.fixture
def provider():
    return FakeProvider()


@pytest.fixture
def secrets():
    return MemorySecrets()


@pytest.fixture
def zenodo(monkeypatch):
    import fair_publishing.zenodo as zenodo_module

    fake = FakeZenodo()
    monkeypatch.setattr(zenodo_module.requests, "post", fake.post)
    monkeypatch.setattr(zenodo_module.requests, "put", fake.put)
    return fake


@pytest.fixture
def make_app(provider, secrets):
    def make(**options):
        app = Flask(__name__)
        app.config.update(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "PUBLISHING_ZENODO_URL": "https://zenodo.test",
                **options.pop("config", {}),
            }
        )
        db = SQLAlchemy()
        db.init_app(app)
        init_publishing(
            app,
            db=db,
            artefact_provider=provider,
            secret_store=secrets,
            login_required=login_required,
            current_owner=lambda: g.user,
            **options,
        )
        with app.app_context():
            PublishingBase.metadata.create_all(db.engine)
        return app

    return make


@pytest.fixture
def app(make_app):
    return make_app()


@pytest.fixture
def client(app):
    return app.test_client()


ALICE = {"X-User": "alice"}
BOB = {"X-User": "bob"}
