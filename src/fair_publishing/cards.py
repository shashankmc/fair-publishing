"""A card template, for when the host offers no LLM draft."""


def template(artefact):
    kind = "Model" if artefact.kind == "model" else "Dataset"
    lines = [f"# {artefact.title}", "", artefact.description or f"Describe what this {kind} is and what it is for.", ""]
    if artefact.task_type:
        lines += ["## Task", "", artefact.task_type.replace("_", " ").capitalize(), ""]
    legal = {name: value for name, value in artefact.legal.items() if value}
    if legal:
        lines += ["## Legal context", ""]
        lines += [f"- {name.replace('_', ' ').capitalize()}: {value}" for name, value in legal.items()]
        lines.append("")
    if artefact.training_dataset:
        lines += ["## Training data", "", f"Trained on the Dataset \"{artefact.training_dataset.get('title', '')}\".", ""]
    if artefact.provenance:
        lines += ["## Where the labels came from", ""]
        sources = artefact.provenance.get("sources") or {}
        lines += [f"- {source.replace('_', ' ')}: {count}" for source, count in sources.items()]
        lines.append("")
    lines += [
        "## Limitations",
        "",
        f"Say where this {kind} should not be used, and what it may get wrong.",
        "",
    ]
    return "\n".join(lines)
