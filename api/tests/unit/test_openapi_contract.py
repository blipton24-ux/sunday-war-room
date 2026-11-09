"""The committed api/openapi.json is what the web client is generated from, so it must match
the code, and it must describe the API honestly (errors included)."""

import json

import pytest

from app.main import app
from app.scripts import export_openapi

SPEC = app.openapi()
OPERATIONS = [
    (method.upper(), path, op) for path, ops in SPEC["paths"].items() for method, op in ops.items()
]


def test_committed_spec_matches_the_code() -> None:
    assert export_openapi.SPEC_PATH.exists(), "run: python -m app.scripts.export_openapi"
    assert export_openapi.read_committed() == export_openapi.current_spec(), (
        "api/openapi.json is stale: run `python -m app.scripts.export_openapi`, "
        "then `npm run generate:api` in web/, and commit both"
    )


def test_operation_ids_are_unique_and_short() -> None:
    ids = [op["operationId"] for _, _, op in OPERATIONS]
    assert len(ids) == len(set(ids)), "two routes share a function name"
    assert all("_api_v1_" not in i for i in ids), ids


def test_render_is_stable() -> None:
    assert export_openapi.render(SPEC) == export_openapi.render(json.loads(json.dumps(SPEC)))


@pytest.mark.parametrize(("method", "path", "op"), OPERATIONS)
def test_every_operation_is_typed_for_the_client(method: str, path: str, op: dict) -> None:  # type: ignore[type-arg]
    """Each operation has a stable operationId and a JSON success body (or 204)."""
    assert op.get("operationId"), f"{method} {path} has no operationId"
    ok = [code for code in op["responses"] if code.startswith("2")]
    assert ok, f"{method} {path} declares no success response"


@pytest.mark.parametrize(("method", "path", "op"), OPERATIONS)
def test_errors_use_the_one_error_shape(method: str, path: str, op: dict) -> None:  # type: ignore[type-arg]
    """No operation advertises FastAPI's default validation-error body: our handler
    returns {detail, code} for every error, and the client types must say so."""
    if path == "/health":
        return
    for code, resp in op["responses"].items():
        if code.startswith(("4", "5")):
            ref = resp["content"]["application/json"]["schema"]["$ref"]
            assert ref.endswith("/ErrorOut"), f"{method} {path} {code} -> {ref}"
    assert "401" in op["responses"], f"{method} {path} doesn't declare 401"


def test_error_schema_is_what_the_handlers_return() -> None:
    err = SPEC["components"]["schemas"]["ErrorOut"]
    assert set(err["properties"]) == {"detail", "code"}
    assert "HTTPValidationError" not in SPEC["components"]["schemas"]
