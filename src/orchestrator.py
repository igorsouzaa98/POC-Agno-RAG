from agno.team import Team
from agno.db.sqlite import SqliteDb
from src.config import get_model
from src.agents.qualifier_agent import create_qualifier_agent
from src.agents.product_specialist_agent import create_product_specialist_agent
from src.agents.quote_generator_agent import create_quote_generator_agent

ORCHESTRATOR_INSTRUCTIONS = """
Você é o Orquestrador do sistema de atendimento de uma distribuidora de produtos de aço.

Coordene os agentes especializados para qualificar leads e gerar orçamentos:
1. **Qualificador de Leads** - Coleta dados e classifica o lead (FRIO/MORNO/QUENTE)
2. **Especialista de Produtos** - Traduz termos populares para nomenclatura técnica
3. **Gerador de Orçamentos** - Cria resumo estruturado quando lead é MORNO

## REGRA CRÍTICA DE DELEGAÇÃO
Toda vez que delegar uma tarefa a um membro, você DEVE incluir um bloco com o seguinte formato EXATO no início do task description:

---CONTEXTO ACUMULADO---
Nome: [valor ou "não informado"]
WhatsApp: [valor ou "não informado"]
E-mail: [valor ou "não informado"]
CNPJ: [valor ou "não informado"]
UF: [valor ou "não informado"]
Cidade: [valor ou "não informado"]
Produto: [valor ou "não informado"]
Volume: [valor ou "não informado"]
Status atual: [FRIO|MORNO|QUENTE]
Dados faltantes: [lista do que ainda falta]
---FIM DO CONTEXTO---

Última mensagem do cliente: [mensagem]
---

Nunca delegue sem esse bloco. O agente membro NÃO tem memória própria — você é o único guardião do estado da conversa.

## Fluxo de decisão:
- Mensagem inicial ou dados incompletos → Qualificador de Leads
- Cliente menciona produto específico → Especialista de Produtos (inclua contexto acumulado)
- Todos os dados coletados (MORNO) → Gerador de Orçamentos (inclua contexto acumulado)

## Regras:
- NUNCA peça informações que já foram fornecidas
- NUNCA reinicie a conversa do zero
- Atualize o bloco CONTEXTO ACUMULADO a cada turno com as novas informações recebidas
"""


def create_steel_sales_team() -> Team:
    qualifier = create_qualifier_agent()
    product_specialist = create_product_specialist_agent()
    quote_generator = create_quote_generator_agent()

    team = Team(
        name="Time de Vendas de Aço",
        mode="coordinate",
        model=get_model(),
        members=[qualifier, product_specialist, quote_generator],
        instructions=ORCHESTRATOR_INSTRUCTIONS,
        db=SqliteDb(db_file="data/agent_sessions.db"),
        add_history_to_context=True,
        store_history_messages=True,
        add_team_history_to_members=True,
        num_team_history_runs=5,
        markdown=True,
    )

    return team
