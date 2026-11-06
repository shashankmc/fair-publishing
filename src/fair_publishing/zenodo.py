"""Zenodo's deposit API, with the user's own personal access token."""
from urllib.parse import quote

import requests

TIMEOUT_SECONDS = 120


class RepositoryError(Exception):
    """The repository refused the deposit or did not answer."""


class Zenodo:
    def __init__(self, base_url, token):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}

    def _check(self, response, step):
        if response.status_code >= 300:
            try:
                message = response.json().get("message")
            except ValueError:
                message = None
            raise RepositoryError(f"Zenodo refused to {step}: {message or response.status_code}")
        return response.json()

    def deposit(self, metadata, files):
        """Create a deposition, upload the files, set the metadata and publish.

        Returns {"doi", "record_url", "record_id"}.
        """
        try:
            created = self._check(
                requests.post(f"{self.base_url}/api/deposit/depositions", json={}, headers=self.headers, timeout=TIMEOUT_SECONDS),
                "create the deposit",
            )
            deposition = created["id"]
            bucket = created["links"]["bucket"]
            for file in files:
                self._check(
                    requests.put(
                        f"{bucket}/{quote(file.name)}",
                        data=file.content,
                        headers={**self.headers, "Content-Type": "application/octet-stream"},
                        timeout=TIMEOUT_SECONDS,
                    ),
                    f"take {file.name}",
                )
            self._check(
                requests.put(
                    f"{self.base_url}/api/deposit/depositions/{deposition}",
                    json={"metadata": metadata},
                    headers=self.headers,
                    timeout=TIMEOUT_SECONDS,
                ),
                "take the metadata",
            )
            published = self._check(
                requests.post(
                    f"{self.base_url}/api/deposit/depositions/{deposition}/actions/publish",
                    headers=self.headers,
                    timeout=TIMEOUT_SECONDS,
                ),
                "publish",
            )
        except requests.RequestException as exc:
            raise RepositoryError(f"Zenodo did not answer: {type(exc).__name__}") from exc
        links = published.get("links", {})
        return {
            "doi": published["doi"],
            "record_url": links.get("record_html") or links.get("html"),
            "record_id": str(published["id"]),
        }
