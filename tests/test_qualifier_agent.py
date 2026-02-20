import pytest
from src.agents.qualifier_agent import create_qualifier_agent


def test_qualifier_agent_created():
    agent = create_qualifier_agent()
    assert agent is not None
    assert agent.name == "Qualificador de Leads"


def test_classify_incomplete_lead_as_frio():
    agent = create_qualifier_agent()
    response = agent.run("Olá, me chamo João, tenho interesse em vergalhão.")
    content = response.content if hasattr(response, 'content') else str(response)
    assert content is not None
    assert any(word in content.lower() for word in ["cnpj", "empresa", "quantidade", "volume", "whatsapp", "email"])
