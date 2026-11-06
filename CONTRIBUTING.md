# Contributing

Thanks for helping improve fair-publishing. Issues and pull requests are welcome at
<https://github.com/shashankmc/fair-publishing>.

## Running the tests

Python 3.11 or newer.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
pytest
```

The suite fakes Zenodo's HTTP API, so it needs no account or network.

CI (`.github/workflows/ci.yml`) runs the same for every push and pull request.

## Cutting a release

1. Move the `[Unreleased]` entries in `CHANGELOG.md` under a new version
   heading with the date, following [Semantic Versioning](https://semver.org/).
2. Set the same version in `pyproject.toml` (and `__version__` in `src/fair_publishing/__init__.py`), `CITATION.cff` (`version`,
   `date-released`), `codemeta.json` (`version`, `dateModified`) and
   `.zenodo.json` (`version`).
3. Commit as `Release X.Y.Z`, tag `vX.Y.Z`, push the tag and create a GitHub
   release from it. Once the repository is connected to Zenodo, each GitHub
   release is archived and receives a DOI.

## Citation metadata the owner still has to fill in

- ORCID: uncomment and fill the `orcid` line in `CITATION.cff`, and add the
  same URL as `"@id"` of the author in `codemeta.json` and as `"orcid"`
  (bare `XXXX-XXXX-XXXX-XXXX`) of the creator in `.zenodo.json`.
- DOI: after the first Zenodo release, add `doi` to `CITATION.cff`,
  `"identifier"` to `codemeta.json`, and the DOI badge to the README.
