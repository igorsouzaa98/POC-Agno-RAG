import pytest
from src.agents.quote_generator_agent import create_quote_generator_agent


def test_quote_generator_created():
    agent = create_quote_generator_agent()
    assert agent is not None
    assert agent.name == "Gerador de Orçamentos"
