import pytest
from src.agents.product_specialist_agent import create_product_specialist_agent


def test_product_specialist_created():
    agent = create_product_specialist_agent()
    assert agent is not None
    assert agent.name == "Especialista de Produtos"
