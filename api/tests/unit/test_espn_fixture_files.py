"""The ESPN fixture files the end-to-end stack serves must match their builders."""

from __future__ import annotations

from tests.export_espn_fixtures import OUT, documents, render


def test_the_committed_fixture_files_match_the_builders() -> None:
    for name, doc in documents().items():
        path = OUT / f"{name}.json"
        assert path.exists(), f"{path.name} is missing: run `python -m tests.export_espn_fixtures`"
        assert path.read_text(encoding="utf-8").replace("\r\n", "\n") == render(doc), (
            f"{path.name} is out of date: run `python -m tests.export_espn_fixtures`"
        )


def test_the_fixtures_hold_no_real_looking_credentials() -> None:
    text = " ".join(render(d) for d in documents().values())
    assert "example.invalid" in text  # logos point nowhere real
    for name, doc in documents().items():
        if name != "cookies":
            assert "espn_s2" not in render(doc)
