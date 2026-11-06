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
