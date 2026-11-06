import json

import pytest

from fair_publishing import Artefact
from tests.conftest import ALICE, BOB

CARD = "# Tenancy clauses\\n\\nClauses from Dutch tenancy agreements, labelled by obligation."


@pytest.fixture
def dataset(provider):
    return provider.add(
        "alice",
        Artefact(
            "dataset", "d1", "Tenancy clauses", "Labelled clauses", "classification",
            legal={"jurisdiction": "NL", "language": "nl", "document_type": "contract", "ecli": None},
            provenance={"sources": {"human": 120, "llm_confirmed": 30}, "models": ["shared-model"], "prompt_versions": [2],
                        "agreement": {"checked": 40, "agreement": 0.9}},
        ),
    )


@pytest.fixture
def connected(client):
    client.put("/api/publishing/token", json={"token": "zen-secret"}, headers=ALICE)


def publish_request(**overrides):
    body = {
        "kind": "dataset",
        "id": "d1",
        "metadata": {
            "title": "Tenancy clauses",
            "description": "Labelled clauses from tenancy agreements.",
            "creators": [{"name": "Doe, Alice", "affiliation": "Maastricht University", "orcid": "0000-0002-1825-0097"}],
            "keywords": ["tenancy", "obligations"],
            "license": "cc-by-4.0",
            "language": "nl",
            "jurisdiction": "NL",
        },
        "access": "open",
        "card": {"text": CARD, "approved": True},
        "attestation": {"license": True, "rights": True, "personal_data": True},
    }
    for key, value in overrides.items():
        body[key] = value
    return body


def publish(client, headers=ALICE, **overrides):
    return client.post("/api/publishing/publish", json=publish_request(**overrides), headers=headers)


def uploaded(zenodo):
    return {call["url"].rsplit("/", 1)[-1]: call["data"] for call in zenodo.of("PUT", "/api/files/")}


def deposited_metadata(zenodo):
    [call] = zenodo.of("PUT", "/api/deposit/depositions/")
    return call["json"]["metadata"]


def test_a_dataset_is_deposited_under_the_users_account_and_registered(client, dataset, connected, zenodo):
    resp = publish(client)

    assert resp.status_code == 201, resp.get_json()
    publication = resp.get_json()["publication"]
    assert publication["doi"] == "10.5072/zenodo.101"
    assert publication["record_url"] == "https://zenodo.test/records/101"
    assert publication["access"] == "open" and publication["license"] == "cc-by-4.0" and publication["mine"] is True
    # Every call is made with the user's own token.
    assert {call["headers"]["Authorization"] for call in zenodo.calls} == {"Bearer zen-secret"}
    assert [c["url"] for c in zenodo.calls if "/actions/publish" in c["url"]] == [
        "https://zenodo.test/api/deposit/depositions/101/actions/publish"
    ]

    registry = client.get("/api/publishing/registry", headers=BOB).get_json()["publications"]
    assert [(p["doi"], p["mine"]) for p in registry] == [("10.5072/zenodo.101", False)]


def test_the_deposit_carries_the_files_card_datacite_ro_crate_and_provenance(client, dataset, connected, zenodo):
    publish(client)

    files = uploaded(zenodo)
    assert set(files) == {"data.csv", "DATASET_CARD.md", "datacite.json", "ro-crate-metadata.json", "provenance.json"}
    assert files["DATASET_CARD.md"].decode() == CARD
    datacite = json.loads(files["datacite.json"])
    assert datacite["titles"] == [{"title": "Tenancy clauses"}]
    assert datacite["types"]["resourceTypeGeneral"] == "Dataset"
    assert datacite["creators"][0]["name"] == "Doe, Alice"
    assert datacite["creators"][0]["nameIdentifiers"] == [
        {"nameIdentifier": "https://orcid.org/0000-0002-1825-0097", "nameIdentifierScheme": "ORCID"}
    ]
    assert datacite["rightsList"] == [{"rightsIdentifier": "cc-by-4.0", "rightsIdentifierScheme": "SPDX"}]
    crate = json.loads(files["ro-crate-metadata.json"])
    root = next(item for item in crate["@graph"] if item["@id"] == "./")
    assert root["name"] == "Tenancy clauses"
    assert root["license"] == {"@id": "https://spdx.org/licenses/CC-BY-4.0"}
    assert root["legislationJurisdiction"] == "NL"
    assert {part["@id"] for part in root["hasPart"]} >= {"data.csv", "DATASET_CARD.md"}
    assert json.loads(files["provenance.json"])["sources"] == {"human": 120, "llm_confirmed": 30}


def test_the_repository_metadata_follows_the_request(client, dataset, connected, zenodo):
    publish(client)

    metadata = deposited_metadata(zenodo)
    assert metadata["title"] == "Tenancy clauses"
    assert metadata["upload_type"] == "dataset"
    assert metadata["access_right"] == "open"
    assert metadata["license"] == "cc-by-4.0"
    assert metadata["creators"] == [{"name": "Doe, Alice", "affiliation": "Maastricht University", "orcid": "0000-0002-1825-0097"}]
    assert metadata["keywords"] == ["tenancy", "obligations"]
    assert metadata["language"] == "nl"
