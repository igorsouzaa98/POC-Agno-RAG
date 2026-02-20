import pytest
from src.orchestrator import create_steel_sales_team


def test_team_created():
    team = create_steel_sales_team()
    assert team is not None


def test_team_has_db():
    """Team deve ter session storage configurado."""
    team = create_steel_sales_team()
    assert team.db is not None


def test_team_has_history_enabled():
    """Team deve ter histórico ativado."""
    team = create_steel_sales_team()
    assert team.add_history_to_context is True
    assert team.store_history_messages is True
    assert team.add_team_history_to_members is True
    assert team.num_team_history_runs == 5
