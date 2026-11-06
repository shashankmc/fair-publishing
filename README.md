# fair-publishing

Publishes datasets and models from a Flask application to a research repository (Zenodo in v1) under the user's own account, with DataCite metadata, RO-Crate, a dataset or model card, legal fields and label provenance, after an attestation of license, rights and personal data. Mounts in-process with init_publishing(app, ...) and receives artefacts from the host through a provider protocol.

Status: in development (BAIGLE issue shashankmc/reducing_digital_divide#69). The
API is not stable before 1.0.

## Installing into a host Flask app

```python
from fair_publishing import init_publishing

init_publishing(app, artefact_provider=..., secret_store=...)
```

The host supplies what is published (an artefact provider) and where each user's
repository token is kept (a secret store). The package does not depend on any ML
library, so a host can publish datasets that have nothing to do with ML.

```python
from fair_publishing import Artefact, DepositFile, RoundTrip, init_publishing

class Artefacts:
    def list(self, owner_id): ...                     # -> [Artefact]
    def get(self, owner_id, kind, artefact_id): ...   # -> Artefact | None
    def files(self, owner_id, artefact): ...          # -> [DepositFile]: the data, or the exported model
    def verify(self, owner_id, artefact): ...         # -> RoundTrip: the model check on the holdout

class Secrets:
    def get(self, owner_id, name): ...
    def set(self, owner_id, name, value): ...
    def delete(self, owner_id, name): ...

init_publishing(
    app,
    db=db,                                  # the host's Flask-SQLAlchemy handle
    artefact_provider=Artefacts(),
    secret_store=Secrets(),                 # keep it encrypted: it holds users' tokens
    login_required=my_login_required,       # the host's sign-in decorator
    current_owner=lambda: current_user_id(),
    feature_gate=lambda owner_id: True,     # optional; on by default
    card_drafter=None,                      # optional: artefact -> card text, e.g. from an LLM
)
```

The HTTP API is in [`docs/openapi.yaml`](docs/openapi.yaml), under `/api/publishing`.

### What publishing checks

- The user attests license, rights and personal data, or nothing is deposited:
  a DOI cannot be withdrawn.
- The host's required metadata fields are filled, the license is one it offers,
  and restricted access says who may get the files.
- The card is approved by the user, including any draft from `card_drafter`.
- A Model points to its training Dataset's DOI, so that Dataset is published
  first (at any access level). The DOI goes into DataCite `relatedIdentifiers`.
- For a Model, `verify` must pass: the exported files predict what the
  platform's Model does on the holdout.
- Each artefact is published once.

### What is deposited

Under the user's own Zenodo account, with their personal access token: the
artefact's files (none for metadata-only access), `DATASET_CARD.md` or
`MODEL_CARD.md`, `datacite.json`, `ro-crate-metadata.json` and `provenance.json`
(where the labels came from). The repository record carries the title,
description, creators, license, keywords, language, access, legal fields and the
related Dataset DOI. The registry then lists it and links to the record.

### Host config

| Setting | Default | |
|---|---|---|
| `PUBLISHING_ZENODO_URL` | `https://zenodo.org` | `https://sandbox.zenodo.org` for testing |
| `PUBLISHING_COMMUNITY` | none | A Zenodo community every deposit is submitted to |
| `PUBLISHING_LICENSES` | CC BY, CC BY-SA, CC BY-NC, CC0, MIT, Apache 2.0 | License ids users may choose |
| `PUBLISHING_REQUIRED_FIELDS` | title, description, creators, license | Also: keywords, language, jurisdiction, document_type, version |

### The registry table

`fair_publishing.models.PublishingBase.metadata` describes it. A host that runs
Alembic can add `fair_publishing/migrations/versions` to its `version_locations`
(branch label `fair_publishing`), or create the same table in its own migration.

## How to cite

If you use fair-publishing in research or teaching, please cite it. The citation
metadata is in [`CITATION.cff`](CITATION.cff) (GitHub's "Cite this repository"
button reads it); [`codemeta.json`](codemeta.json) carries the same metadata in
CodeMeta form.

> Chakravarthy, S. (2026). *fair-publishing* (Version 0.1.0) [Computer software].
> Maastricht University. https://github.com/shashankmc/fair-publishing

**DOI:** not yet assigned. Once the repository is connected to Zenodo, each
GitHub release will be archived there and its DOI (and a DOI badge) will be
added to this section and to `CITATION.cff`.

The user interface is [vue-fair-publisher](https://github.com/shashankmc/vue-fair-publisher);
cite both if you use both.

## License

MIT, see [LICENSE](LICENSE).
