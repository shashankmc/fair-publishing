from fair_publishing import Artefact
from tests.conftest import ALICE, BOB


def test_the_token_is_write_only_and_kept_per_user(client, secrets):
    assert client.get("/api/publishing/token", headers=ALICE).get_json() == {"connected": False}

    saved = client.put("/api/publishing/token", json={"token": " zen-secret "}, headers=ALICE)

    assert saved.status_code == 200
    assert saved.get_json() == {"connected": True}
    assert "zen-secret" not in saved.get_data(as_text=True)
    assert secrets.get("alice", "zenodo_token") == "zen-secret"
    assert client.get("/api/publishing/token", headers=ALICE).get_json() == {"connected": True}
    assert client.get("/api/publishing/token", headers=BOB).get_json() == {"connected": False}


def test_an_empty_token_is_refused(client):
    resp = client.put("/api/publishing/token", json={"token": "  "}, headers=ALICE)

    assert resp.status_code == 400
    assert resp.get_json()["code"] == "token_missing"


def test_the_token_can_be_deleted(client, secrets):
    client.put("/api/publishing/token", json={"token": "zen-secret"}, headers=ALICE)

    assert client.delete("/api/publishing/token", headers=ALICE).status_code == 204
    assert secrets.get("alice", "zenodo_token") is None


def test_artefacts_are_the_users_own_from_the_host(client, provider):
    provider.add("alice", Artefact("dataset", "d1", "Tenancy clauses", "Labelled clauses", "classification",
                                   legal={"jurisdiction": "NL", "language": "nl"}))
    provider.add("alice", Artefact("model", "m1", "Clause classifier", training_dataset={"id": "d1", "title": "Tenancy clauses"}))
    provider.add("bob", Artefact("dataset", "d9", "Bob's"))

    artefacts = client.get("/api/publishing/artefacts", headers=ALICE).get_json()["artefacts"]

    assert [(a["kind"], a["id"]) for a in artefacts] == [("dataset", "d1"), ("model", "m1")]
    dataset, model = artefacts
    assert dataset["legal"] == {"jurisdiction": "NL", "language": "nl"}
    assert dataset["publication"] is None
    assert model["training_dataset"] == {"id": "d1", "title": "Tenancy clauses", "doi": None}
