"""What a deposit says about itself: repository metadata, DataCite and RO-Crate."""
from datetime import date

SPDX = {
    "cc-by-4.0": "CC-BY-4.0",
    "cc-by-sa-4.0": "CC-BY-SA-4.0",
    "cc-by-nc-4.0": "CC-BY-NC-4.0",
    "cc0-1.0": "CC0-1.0",
    "mit": "MIT",
    "apache-2.0": "Apache-2.0",
}
ZENODO_ACCESS = {"open": "open", "restricted": "restricted", "metadata_only": "closed"}
LEGAL_FIELDS = ("jurisdiction", "language", "document_type", "ecli")


def card_name(kind):
    return "MODEL_CARD.md" if kind == "model" else "DATASET_CARD.md"


def legal_fields(artefact, metadata):
    """The request's legal fields, falling back to what the host knows."""
    return {name: metadata.get(name) or artefact.legal.get(name) for name in LEGAL_FIELDS}


def _orcid_url(orcid):
    return orcid if orcid.startswith("http") else f"https://orcid.org/{orcid}"


def zenodo_metadata(artefact, metadata, access, access_conditions, related_doi, community):
    legal = legal_fields(artefact, metadata)
    body = {
        "title": metadata["title"],
        # Zenodo's deposit API has no model type.
        "upload_type": "dataset" if artefact.kind == "dataset" else "other",
        "description": metadata.get("description") or metadata["title"],
        "creators": [
            {key: creator[key] for key in ("name", "affiliation", "orcid") if creator.get(key)}
            for creator in metadata.get("creators", [])
        ],
        "access_right": ZENODO_ACCESS[access],
        "license": metadata.get("license"),
        "keywords": metadata.get("keywords") or [],
    }
    if access == "restricted":
        body["access_conditions"] = access_conditions
    if legal["language"]:
        body["language"] = legal["language"]
    if metadata.get("version"):
        body["version"] = metadata["version"]
    if related_doi:
        body["related_identifiers"] = [
            {"identifier": related_doi, "relation": "isDerivedFrom", "scheme": "doi", "resource_type": "dataset"}
        ]
    if community:
        body["communities"] = [{"identifier": community}]
    notes = [f"{name.replace('_', ' ').capitalize()}: {value}" for name, value in legal.items() if value]
    if notes:
        body["notes"] = "; ".join(notes)
    return body


def datacite(artefact, metadata, related_doi):
    legal = legal_fields(artefact, metadata)
    body = {
        "titles": [{"title": metadata["title"]}],
        "creators": [
            {
                "name": creator["name"],
                "nameType": "Personal",
                "affiliation": [{"name": creator["affiliation"]}] if creator.get("affiliation") else [],
                "nameIdentifiers": (
                    [{"nameIdentifier": _orcid_url(creator["orcid"]), "nameIdentifierScheme": "ORCID"}]
                    if creator.get("orcid")
                    else []
                ),
            }
            for creator in metadata.get("creators", [])
        ],
        "publisher": "Zenodo",
        "publicationYear": str(date.today().year),
        "types": {
            "resourceTypeGeneral": "Model" if artefact.kind == "model" else "Dataset",
            "resourceType": artefact.task_type or artefact.kind,
        },
        "descriptions": [{"description": metadata.get("description", ""), "descriptionType": "Abstract"}],
        "subjects": [{"subject": keyword} for keyword in metadata.get("keywords") or []],
        "rightsList": [{"rightsIdentifier": metadata.get("license"), "rightsIdentifierScheme": "SPDX"}],
    }
    if legal["language"]:
        body["language"] = legal["language"]
    if metadata.get("version"):
        body["version"] = metadata["version"]
    if related_doi:
        body["relatedIdentifiers"] = [
            {
                "relatedIdentifier": related_doi,
                "relatedIdentifierType": "DOI",
                "relationType": "IsDerivedFrom",
                "resourceTypeGeneral": "Dataset",
            }
        ]
    return body


def ro_crate(artefact, metadata, files, related_doi):
    legal = legal_fields(artefact, metadata)
    people = []
    for index, creator in enumerate(metadata.get("creators", [])):
        person = {"@id": _orcid_url(creator["orcid"]) if creator.get("orcid") else f"#creator-{index}", "@type": "Person", "name": creator["name"]}
        if creator.get("affiliation"):
            person["affiliation"] = creator["affiliation"]
        people.append(person)
    license_id = SPDX.get(metadata.get("license"), metadata.get("license"))
    root = {
        "@id": "./",
        "@type": "Dataset",
        "name": metadata["title"],
        "description": metadata.get("description", ""),
        "datePublished": date.today().isoformat(),
        "license": {"@id": f"https://spdx.org/licenses/{license_id}"},
        "author": [{"@id": person["@id"]} for person in people],
        "keywords": metadata.get("keywords") or [],
        "hasPart": [{"@id": file.name} for file in files],
    }
    if legal["language"]:
        root["inLanguage"] = legal["language"]
    if legal["jurisdiction"]:
        root["legislationJurisdiction"] = legal["jurisdiction"]
    if legal["document_type"]:
        root["legislationType"] = legal["document_type"]
    if legal["ecli"]:
        root["identifier"] = legal["ecli"]
    if related_doi:
        root["isBasedOn"] = {"@id": f"https://doi.org/{related_doi}"}
    return {
        "@context": "https://w3id.org/ro/crate/1.1/context",
        "@graph": [
            {
                "@id": "ro-crate-metadata.json",
                "@type": "CreativeWork",
                "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
                "about": {"@id": "./"},
            },
            root,
            *({"@id": file.name, "@type": "File", "contentSize": str(len(file.content))} for file in files),
            *people,
        ],
    }
