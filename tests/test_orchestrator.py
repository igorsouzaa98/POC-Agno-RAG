import pytest
from src.orchestrator import create_steel_sales_team


def test_team_created():
    team = create_steel_sales_team()
    assert team is not None
