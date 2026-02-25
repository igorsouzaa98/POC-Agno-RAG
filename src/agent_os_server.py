"""
Servidor AgentOS — integração com o Agent UI (frontend Agno).

Como usar:
  1. Inicie este servidor: python src/agent_os_server.py
  2. Em outro terminal, rode o frontend: npx create-agent-ui@latest
  3. Acesse http://localhost:3001 e conecte em http://localhost:7777
"""
import sys
sys.path.insert(0, '.')

from agno.os import AgentOS
from src.agents.qualifier_agent import create_qualifier_agent
from src.agents.product_specialist_agent import create_product_specialist_agent
from src.agents.quote_generator_agent import create_quote_generator_agent
from src.orchestrator import create_steel_sales_team

# Agentes individuais disponíveis no UI
qualifier = create_qualifier_agent()
product_specialist = create_product_specialist_agent()
quote_generator = create_quote_generator_agent()

# Time completo (orquestrador)
steel_team = create_steel_sales_team()

agent_os = AgentOS(
    name="Vendas de Aço",
    description="Sistema de qualificação de leads e geração de orçamentos para distribuidora de aço",
    agents=[qualifier, product_specialist, quote_generator],
    teams=[steel_team],
    cors_allowed_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://agent-ui-smoky.vercel.app",
    ],
)

app = agent_os.get_app()

if __name__ == "__main__":
    print("=" * 60)
    print("  POC AGNO - Servidor AgentOS")
    print("  Porta: http://localhost:7777")
    print("  Docs:  http://localhost:7777/docs")
    print("=" * 60)
    print("\nAgentes disponíveis no UI:")
    print("  - Qualificador de Leads")
    print("  - Especialista de Produtos")
    print("  - Gerador de Orçamentos")
    print("  - Time de Vendas de Aço (orquestrador)")
    print("\nConecte o Agent UI em: http://localhost:7777")
    print("=" * 60)
    agent_os.serve(app="src.agent_os_server:app", reload=True)
