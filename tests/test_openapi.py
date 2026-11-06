"""docs/openapi.yaml describes exactly the routes the package registers."""
import pathlib

import yaml

SPEC = pathlib.Path(__file__).parent.parent / "docs/openapi.yaml"


def test_every_route_is_in_the_spec_and_nothing_else(app):
    spec = yaml.safe_load(SPEC.read_text())
    documented = {
        (path, method.upper()) for path, item in spec["paths"].items() for method in item if method in ("get", "put", "post", "delete")
    }
    registered = {
        (rule.rule.replace("<", "{").replace(">", "}"), method)
        for rule in app.url_map.iter_rules()
        if rule.endpoint.startswith("fair_publishing.")
        for method in rule.methods - {"HEAD", "OPTIONS"}
    }

    assert registered == documented
