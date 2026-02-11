"""Tests for the HTMX explore openings view."""

import pytest
from django.test import Client

from chess_core.models import Opening
from chess_core.tests.factories import GameFactory, OpeningFactory


@pytest.fixture
def client() -> Client:
    """Django test client."""
    return Client()


@pytest.fixture
def opening_with_games(db) -> Opening:
    """Opening with games for filtered results."""
    opening = OpeningFactory(eco_code="B20", name="Sicilian Defense")
    for _ in range(3):
        GameFactory(opening=opening, result="1-0", move_count_ply=40)
    GameFactory(opening=opening, result="1/2-1/2", move_count_ply=50)
    GameFactory(opening=opening, result="0-1", move_count_ply=60)
    return opening


def test_explore_full_page_returns_200(client: Client, db: None) -> None:
    """GET /explore/ without params returns 200 and results container."""
    response = client.get("/explore/")
    assert response.status_code == 200
    assert b"explore-results" in response.content
    assert b"Explore openings" in response.content
    assert b"win-rate-chart-wrapper" in response.content


def test_explore_full_page_empty_state(client: Client, db: None) -> None:
    """Full page with no data shows empty message in initial render."""
    response = client.get("/explore/")
    assert response.status_code == 200
    assert b"No openings match the filters" in response.content


def test_explore_full_page_with_data(
    client: Client, db: None, opening_with_games: Opening
) -> None:
    """Full page with data shows table and total."""
    response = client.get(
        "/explore/",
        {"threshold": "5", "opening_threshold": "1"},
    )
    assert response.status_code == 200
    assert b"Sicilian Defense" in response.content
    assert b"B20" in response.content
    assert b"1 opening" in response.content


def test_explore_htmx_returns_partial_only(client: Client, db: None) -> None:
    """Request with HX-Request returns chart + table partial, no full layout."""
    response = client.get("/explore/", HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "<html" not in content.lower()
    assert "win-rate-chart-data" in content
    assert "win-rate-chart-wrapper" in content
    assert "No openings match" in content or "Total:" in content


def test_explore_htmx_with_data_returns_table(
    client: Client, db: None, opening_with_games: Opening
) -> None:
    """HTMX request with data returns table fragment."""
    response = client.get(
        "/explore/",
        {"threshold": "5", "opening_threshold": "1"},
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 200
    assert b"Sicilian Defense" in response.content
    assert b"B20" in response.content


def test_explore_invalid_threshold_no_500(client: Client, db: None) -> None:
    """Invalid threshold (e.g. non-integer) does not cause 500."""
    response = client.get("/explore/", {"threshold": "abc"})
    assert response.status_code == 200
    assert b"Invalid filters" in response.content or b"explore" in response.content


def test_explore_valid_filters_repopulate_form(
    client: Client, db: None, opening_with_games: Opening
) -> None:
    """Valid GET params are reflected in form_data (input values)."""
    response = client.get(
        "/explore/",
        {"threshold": "5", "eco_code": "B20"},
    )
    assert response.status_code == 200
    assert b'value="B20"' in response.content
    assert b'value="5"' in response.content
