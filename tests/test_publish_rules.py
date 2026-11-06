import json

import pytest

from fair_publishing import Artefact, RoundTrip
from tests.conftest import ALICE
from tests.test_publish import connected, dataset, deposited_metadata, publish, publish_request, uploaded  # noqa: F401


def refused(resp, status, code):
    assert resp.status_code == status, resp.get_json()
    assert resp.get_json()["code"] == code
    return resp.get_json()


@pytest.mark.parametrize("missing", ["license", "rights", "personal_data"])
def test_nothing_is_deposited_without_every_attestation(client, dataset, connected, zenodo, missing):
    attestation = {"license": True, "rights": True, "personal_data": True, missing: False}

    body = refused(publish(client, attestation=attestation), 400, "attestation_required")

    assert body["missing"] == [missing]
    assert zenodo.calls == []


def test_required_fields_are_named(client, dataset, connected, zenodo):
    metadata = {**publish_request()["metadata"], "description": " ", "creators": [{"name": ""}]}

    body = refused(publish(client, metadata=metadata), 400, "missing_fields")

    assert body["missing"] == ["description", "creators"]
    assert zenodo.calls == []


def test_only_offered_licenses_and_known_access_levels(client, dataset, connected, zenodo):
    refused(publish(client, metadata={**publish_request()["metadata"], "license": "proprietary"}), 400, "invalid_license")
    refused(publish(client, access="public"), 400, "invalid_access")
    refused(publish(client, access="restricted"), 400, "access_conditions_required")
    assert zenodo.calls == []


def test_the_card_must_be_approved(client, dataset, connected, zenodo):
    refused(publish(client, card={"text": "# Draft by an LLM", "approved": False}), 400, "card_not_approved")
    assert zenodo.calls == []


def test_without_a_token_nothing_is_deposited(client, dataset, zenodo):
    refused(publish(client), 403, "token_required")
    assert zenodo.calls == []


def test_someone_elses_artefact_is_not_found(client, provider, connected, zenodo):
    provider.add("bob", Artefact("dataset", "d1", "Bob's"))

    refused(publish(client), 404, "not_found")


def test_an_artefact_is_published_once(client, dataset, connected, zenodo):
    assert publish(client).status_code == 201

    refused(publish(client), 409, "already_published")


def test_restricted_access_says_who_may_get_the_files(client, dataset, connected, zenodo):
    publish(client, access="restricted", access_conditions="Researchers at Dutch universities, on request.")

    metadata = deposited_metadata(zenodo)
    assert metadata["access_right"] == "restricted"
    assert metadata["access_conditions"] == "Researchers at Dutch universities, on request."


def test_metadata_only_deposits_no_data(client, dataset, connected, zenodo):
    publish(client, access="metadata_only")

    assert deposited_metadata(zenodo)["access_right"] == "closed"
    assert "data.csv" not in uploaded(zenodo)
    assert "DATASET_CARD.md" in uploaded(zenodo)


def test_a_repository_failure_publishes_nothing(client, dataset, connected, zenodo):
    zenodo.fail = True

    refused(publish(client), 502, "repository_failed")
    assert client.get("/api/publishing/registry", headers=ALICE).get_json()["publications"] == []


@pytest.fixture
def model(provider):
    return provider.add(
        "alice",
        Artefact("model", "m1", "Clause classifier", "An SVM", "classification", training_dataset={"id": "d1", "title": "Tenancy clauses"}),
    )


def model_request(**overrides):
    return publish_request(kind="model", id="m1", **overrides)


def test_a_model_needs_its_training_dataset_published_first(client, dataset, model, connected, zenodo):
    resp = client.post("/api/publishing/publish", json=model_request(), headers=ALICE)

    body = refused(resp, 409, "dataset_doi_required")
    assert body["training_dataset"] == {"id": "d1", "title": "Tenancy clauses"}
    assert zenodo.calls == []


def test_a_model_points_to_its_datasets_doi(client, dataset, model, connected, zenodo):
    assert publish(client).status_code == 201
    zenodo.calls.clear()

    resp = client.post("/api/publishing/publish", json=model_request(), headers=ALICE)

    assert resp.status_code == 201, resp.get_json()
    assert resp.get_json()["publication"]["related_dataset_doi"] == "10.5072/zenodo.101"
    files = uploaded(zenodo)
    assert set(files) >= {"model.skops", "preprocessing.json", "MODEL_CARD.md"}
    assert json.loads(files["datacite.json"])["relatedIdentifiers"] == [
        {"relatedIdentifier": "10.5072/zenodo.101", "relatedIdentifierType": "DOI", "relationType": "IsDerivedFrom", "resourceTypeGeneral": "Dataset"}
    ]
    assert json.loads(files["datacite.json"])["types"]["resourceTypeGeneral"] == "Model"
    assert deposited_metadata(zenodo)["related_identifiers"][0]["identifier"] == "10.5072/zenodo.101"


def test_a_model_that_fails_the_round_trip_is_not_published(client, provider, dataset, model, connected, zenodo):
    publish(client)
    zenodo.calls.clear()
    provider.round_trip = RoundTrip(ok=False, detail="3 of 20 held-back predictions differ.")

    resp = client.post("/api/publishing/publish", json=model_request(), headers=ALICE)

    body = refused(resp, 422, "round_trip_failed")
    assert body["detail"] == "3 of 20 held-back predictions differ."
    assert zenodo.calls == []


def test_the_preview_shows_the_deposit_without_making_it(client, dataset, zenodo):
    resp = client.post("/api/publishing/preview", json=publish_request(attestation={}), headers=ALICE)

    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert {f["name"] for f in body["files"]} == {"data.csv", "DATASET_CARD.md", "provenance.json", "datacite.json", "ro-crate-metadata.json"}
    assert body["datacite"]["titles"] == [{"title": "Tenancy clauses"}]
    assert zenodo.calls == []


def test_the_card_is_drafted_from_a_template_or_by_the_hosts_drafter(make_app, provider):
    provider.add("alice", Artefact("dataset", "d1", "Tenancy clauses", legal={"jurisdiction": "NL"}))
    template = make_app().test_client().post("/api/publishing/card-draft", json={"kind": "dataset", "id": "d1"}, headers=ALICE)
    assert template.get_json()["source"] == "template"
    assert template.get_json()["card"].startswith("# Tenancy clauses")
    assert "Jurisdiction: NL" in template.get_json()["card"]

    drafted = make_app(card_drafter=lambda artefact: f"# {artefact.title}\n\nDrafted.").test_client().post(
        "/api/publishing/card-draft", json={"kind": "dataset", "id": "d1"}, headers=ALICE
    )
    assert drafted.get_json() == {"card": "# Tenancy clauses\n\nDrafted.", "source": "llm"}


def test_the_registry_is_searchable(client, provider, dataset, connected, zenodo):
    provider.add("alice", Artefact("dataset", "d2", "Court rulings"))
    publish(client)
    publish(client, id="d2", metadata={**publish_request()["metadata"], "title": "Court rulings", "keywords": ["ECLI"]})

    def titles(**params):
        resp = client.get("/api/publishing/registry", query_string=params, headers=ALICE)
        return sorted(p["title"] for p in resp.get_json()["publications"])

    assert titles() == ["Court rulings", "Tenancy clauses"]
    assert titles(q="ecli") == ["Court rulings"]
    assert titles(kind="model") == []
    first = client.get("/api/publishing/registry", headers=ALICE).get_json()["publications"][0]
    assert client.get(f"/api/publishing/registry/{first['id']}", headers=ALICE).get_json()["publication"]["doi"] == first["doi"]
