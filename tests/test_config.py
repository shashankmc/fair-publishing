from tests.conftest import ALICE


def test_the_config_says_what_this_host_allows(client):
    resp = client.get("/api/publishing/config", headers=ALICE)

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["enabled"] is True
    assert body["repository"] == {
        "id": "zenodo",
        "name": "Zenodo",
        "sandbox": False,
        "token_url": "https://zenodo.test/account/settings/applications/tokens/new/",
    }
    assert {"id": "cc-by-4.0", "title": "Creative Commons Attribution 4.0 International"} in body["licenses"]
    assert body["required_fields"] == ["title", "description", "creators", "license"]
    assert body["access_levels"] == ["open", "restricted", "metadata_only"]
    assert body["community"] is None


def test_the_host_chooses_licenses_fields_and_community(make_app):
    app = make_app(config={
        "PUBLISHING_LICENSES": ["cc0-1.0"],
        "PUBLISHING_REQUIRED_FIELDS": ["title", "language"],
        "PUBLISHING_COMMUNITY": "legal-nlp",
        "PUBLISHING_ZENODO_URL": "https://sandbox.zenodo.org",
    })

    body = app.test_client().get("/api/publishing/config", headers=ALICE).get_json()

    assert [lic["id"] for lic in body["licenses"]] == ["cc0-1.0"]
    assert body["required_fields"] == ["title", "language"]
    assert body["community"] == "legal-nlp"
    assert body["repository"]["sandbox"] is True


def test_a_host_can_turn_publishing_off_for_a_user(make_app):
    app = make_app(feature_gate=lambda owner_id: owner_id != "alice")
    client = app.test_client()

    assert client.get("/api/publishing/config", headers=ALICE).get_json()["enabled"] is False
    refused = client.get("/api/publishing/artefacts", headers=ALICE)
    assert refused.status_code == 403
    assert refused.get_json()["code"] == "publishing_disabled"


def test_every_route_needs_the_hosts_sign_in(client):
    assert client.get("/api/publishing/config").status_code == 401
