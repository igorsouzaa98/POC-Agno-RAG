from agno.team import Team
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

## Fluxo:
- Mensagem inicial → Qualificador de Leads
- Produto mencionado → Especialista de Produtos
- Todos os dados coletados (MORNO) → Gerador de Orçamentos

Sempre mantenha o contexto da conversa e classifique o lead ao final.
"""


def create_steel_sales_team() -> Team:
    qualifier = create_qualifier_agent()
    product_specialist = create_product_specialist_agent()
    quote_generator = create_quote_generator_agent()

    # TeamMode.coordinate is confirmed valid in Agno 2.5.3
    team = Team(
        name="Time de Vendas de Aço",
        mode="coordinate",
        model=get_model(),
        members=[qualifier, product_specialist, quote_generator],
        instructions=ORCHESTRATOR_INSTRUCTIONS,
        markdown=True,
    )

    return team
