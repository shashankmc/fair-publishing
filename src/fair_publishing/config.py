"""Host settings, read from the Flask config."""
from flask import current_app

LICENSE_TITLES = {
    "cc-by-4.0": "Creative Commons Attribution 4.0 International",
    "cc-by-sa-4.0": "Creative Commons Attribution Share Alike 4.0 International",
    "cc-by-nc-4.0": "Creative Commons Attribution Non Commercial 4.0 International",
    "cc0-1.0": "Creative Commons Zero v1.0 Universal",
    "mit": "MIT License",
    "apache-2.0": "Apache License 2.0",
}
DEFAULT_LICENSES = ["cc-by-4.0", "cc-by-sa-4.0", "cc-by-nc-4.0", "cc0-1.0", "mit", "apache-2.0"]
DEFAULT_REQUIRED_FIELDS = ["title", "description", "creators", "license"]
ACCESS_LEVELS = ["open", "restricted", "metadata_only"]
ZENODO_URL = "https://zenodo.org"


def setting(name, default=None):
    return current_app.config.get(name, default)


def licenses():
    return [{"id": lic, "title": LICENSE_TITLES.get(lic, lic)} for lic in setting("PUBLISHING_LICENSES", DEFAULT_LICENSES)]


def required_fields():
    return list(setting("PUBLISHING_REQUIRED_FIELDS", DEFAULT_REQUIRED_FIELDS))


def zenodo_url():
    return setting("PUBLISHING_ZENODO_URL", ZENODO_URL).rstrip("/")


def community():
    return setting("PUBLISHING_COMMUNITY")
