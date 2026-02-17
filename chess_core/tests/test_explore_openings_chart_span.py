"""Tests for explore_openings chart time-span behaviour."""

from datetime import date

import pytest
from django.test import Client


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.mark.django_db
def test_chart_hidden_for_short_date_range(client: Client) -> None:
    """Chart is not rendered when date range is shorter than 14 days."""
    response = client.get(
        "/explore/",
        {
            "date_from": date(2024, 1, 1).isoformat(),
            "date_to": date(2024, 1, 7).isoformat(),
        },
    )
    content = response.content.decode("utf-8")
    assert "Increase date range to generate historical chart" in content
    assert 'id="win-rate-chart"' not in content

