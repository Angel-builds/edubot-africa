"""The student-facing page.

Students pay for every byte over mobile data, so the weight budget is asserted
rather than hoped for. The contract test matters just as much: the page talks to
/chat by hand-written field names, and nothing else would notice them drifting.
"""

from __future__ import annotations

import gzip
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app

PAGE = Path("web/index.html")

# PRD decision 12: under 100 KB first paint, under 20 KB per Turn.
FIRST_PAINT_BUDGET = 100 * 1024
TURN_BUDGET = 20 * 1024

client = TestClient(app)


@pytest.fixture(scope="module")
def markup() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_page_is_served_at_the_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_first_paint_fits_the_budget(markup):
    raw = markup.encode()
    assert len(raw) < FIRST_PAINT_BUDGET
    assert len(gzip.compress(raw)) < FIRST_PAINT_BUDGET


def test_page_makes_no_external_requests(markup):
    """A webfont or CDN script is a round trip the student pays for, and a
    dependency that fails on a bad connection."""
    assert "<script src=" not in markup
    assert "<link" not in markup or "stylesheet" not in markup
    offsite = [
        url for url in re.findall(r'(?:src|href)=["\'](https?://[^"\']+)', markup)
    ]
    assert offsite == []


def test_a_turn_fits_the_budget():
    body = {"question": "3x + 5 = 20", "hint_level": 0}
    response = client.post("/chat", json=body)
    assert response.status_code == 200
    assert len(response.content) < TURN_BUDGET


def test_page_uses_the_current_chat_contract(markup):
    """The page builds its request by hand. If the API renames a field, nothing
    else in the suite would catch it -- the page would just stop working."""
    schema = client.get("/openapi.json").json()["components"]["schemas"]

    for field in schema["Ask"]["properties"]:
        assert field in markup, f"/chat accepts {field!r} but the page never sends it"

    for field in schema["Reply"]["properties"]:
        assert field in markup, f"/chat returns {field!r} but the page never reads it"

    for field in ("heading", "url", "attribution", "grade"):
        assert field in markup, f"Citation.{field} is never displayed"


def test_attribution_is_displayed(markup):
    """CC BY requires the credit line to be shown, not merely stored."""
    assert "attribution" in markup


def test_hint_ladder_is_visible_to_the_student(markup):
    """Being asked 'what have you tried?' reads as a refusal unless the student
    can see they are being coached through five steps."""
    assert "hint " in markup and "RUNGS" in markup
