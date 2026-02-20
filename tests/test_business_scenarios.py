"""
Cenários de teste baseados nos casos definidos pelo negócio.
Estes testes são de integração e requerem ANTHROPIC_API_KEY configurada.
Execute com: pytest tests/test_business_scenarios.py -v -m "not integration" para testes estruturais
Execute com: pytest tests/test_business_scenarios.py -v para todos os testes (requer API key)
"""
import os
import pytest
from src.models import LeadClassification


# Marca testes que precisam de API key real
needs_api = pytest.mark.skipif(
    os.getenv("ANTHROPIC_API_KEY", "your_anthropic_api_key_here") == "your_anthropic_api_key_here"
    or not os.getenv("ANTHROPIC_API_KEY"),
    reason="Requer ANTHROPIC_API_KEY configurada"
)


class TestModelos:
    """Testes estruturais dos modelos de domínio"""

    def test_lead_classification_values(self):
        assert LeadClassification.FRIO == "FRIO"
        assert LeadClassification.MORNO == "MORNO"
        assert LeadClassification.QUENTE == "QUENTE"

    def test_lead_frio_is_default(self):
        from src.models import LeadData
        lead = LeadData(session_id="test")
        assert lead.classification == LeadClassification.FRIO

    def test_lead_data_missing_fields_default(self):
        from src.models import LeadData
        lead = LeadData(session_id="test")
        assert lead.missing_fields == []

    def test_incoming_message_model(self):
        from src.models import IncomingMessage
        msg = IncomingMessage(session_id="sess-001", message="Olá")
        assert msg.session_id == "sess-001"
        assert msg.lead_data is None

    def test_agent_response_model(self):
        from src.models import AgentResponse, LeadData
        lead = LeadData(session_id="test")
        resp = AgentResponse(
            session_id="test",
            message="Olá",
            classification=LeadClassification.FRIO,
            lead_data=lead,
            next_action="collect_data"
        )
        assert resp.next_action == "collect_data"


class TestAgentesEstrutura:
    """Testes estruturais dos agentes (sem chamada à API)"""

    def test_qualifier_agent_has_correct_name(self):
        from src.agents.qualifier_agent import create_qualifier_agent
        agent = create_qualifier_agent()
        assert agent.name == "Qualificador de Leads"

    def test_product_specialist_has_correct_name(self):
        from src.agents.product_specialist_agent import create_product_specialist_agent
        agent = create_product_specialist_agent()
        assert agent.name == "Especialista de Produtos"

    def test_quote_generator_has_correct_name(self):
        from src.agents.quote_generator_agent import create_quote_generator_agent
        agent = create_quote_generator_agent()
        assert agent.name == "Gerador de Orçamentos"

    def test_orchestrator_team_created(self):
        from src.orchestrator import create_steel_sales_team
        team = create_steel_sales_team()
        assert team is not None
        assert len(team.members) == 3

    def test_api_health_endpoint(self):
        from fastapi.testclient import TestClient
        from src.api import app
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestFluxoQualificacao:
    """Testes de integração - requerem API key"""

    @needs_api
    def test_lead_frio_solicita_dados(self):
        from src.orchestrator import create_steel_sales_team
        team = create_steel_sales_team()
        response = team.run("Quero comprar aço")
        content = response.content if hasattr(response, 'content') else str(response)
        assert any(w in content.lower() for w in ["nome", "empresa", "cnpj", "dados"])

    @needs_api
    def test_traducao_ferro_para_vergalhao(self):
        from src.agents.product_specialist_agent import create_product_specialist_agent
        agent = create_product_specialist_agent()
        response = agent.run("Preciso de ferro para laje, uns 10mm, umas 5 toneladas")
        content = response.content if hasattr(response, 'content') else str(response)
        assert any(w in content.lower() for w in ["vergalhão", "ca 60", "si 50"])

    @needs_api
    def test_traducao_metalon_para_tubo(self):
        from src.agents.product_specialist_agent import create_product_specialist_agent
        agent = create_product_specialist_agent()
        response = agent.run("Quero metalon 30x30mm")
        content = response.content if hasattr(response, 'content') else str(response)
        assert any(w in content.lower() for w in ["tubo", "quadrado"])

    @needs_api
    def test_lead_completo_gera_resumo(self):
        from src.orchestrator import create_steel_sales_team
        team = create_steel_sales_team()
        mensagem = """
        Olá! Sou da Construtora Horizonte.
        Nome: Carlos Mendes
        WhatsApp: 11977776666
        Email: carlos@construtora.com.br
        CNPJ: 45.678.901/0001-23
        Estamos em Belo Horizonte - MG
        Preciso de 20 toneladas de vergalhão CA 60 12.5mm
        Urgência: até 30 dias
        """
        response = team.run(mensagem)
        content = response.content if hasattr(response, 'content') else str(response)
        assert any(w in content.lower() for w in ["morno", "orçamento", "resumo", "pedido", "carlos"])
