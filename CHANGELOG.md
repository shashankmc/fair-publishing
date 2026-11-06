# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the version is 0.x, minor releases may contain breaking changes.

## [Unreleased]

## [0.1.0] - 2026-11-06

### Added

- `init_publishing(app, ...)`: publishing datasets and models to Zenodo under the
  user's own account, through a host-supplied artefact provider and secret store,
  with a host feature gate (on by default), and the HTTP API in
  `docs/openapi.yaml`: config, a write-only token, the user's artefacts, a card
  draft (template, or the host's drafter), preview, publish and the registry.
- Publishing requires the license, rights and personal data attestation, the
  host's required fields, an approved card, the training Dataset's DOI for a
  Model, and a passing round trip for a Model. Open, restricted and
  metadata-only access.
- Each deposit carries DataCite metadata, RO-Crate metadata, the card, legal
  fields and label provenance.
- The `publications` registry table, with an Alembic revision for hosts.
- Repository set up with its FAIR4RS metadata (CITATION.cff, codemeta.json,
  .zenodo.json), license, contributing guide and CI.

[Unreleased]: https://github.com/shashankmc/fair-publishing/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/shashankmc/fair-publishing/releases/tag/v0.1.0
