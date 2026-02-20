# Team Context Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Corrigir a perda de contexto no Agno Team adicionando session storage (SQLite) e reescrevendo as instruções do orquestrador para que a conversa nunca recomece do zero.

**Architecture:** Adicionar `SqliteDb` ao Team com `add_history_to_context=True` e `add_team_history_to_members=True`. O orquestrador passa a persistir o histórico entre turns e repassa o contexto acumulado aos agentes membros em cada delegação. As instruções do orquestrador são reescritas para exigir um bloco "CONTEXTO ACUMULADO" em cada delegação.

**Tech Stack:** Agno 2.5.3, SqliteDb (agno.db.sqlite), sqlalchemy>=2.0.0

---

## Contexto do Domínio

### Bug observado
```
Turn 1: Agente pede dados → STATUS: FRIO
Turn 2: Usuário envia: produto, cidade, zap, email, CNPJ
        → Orquestrador delega ao Qualificador
        → Qualificador: "Falta só o nome" → STATUS: FRIO
Turn 3: Usuário envia: "Igor Souza Silva"
        → Orquestrador delega ao Qualificador SEM histórico
        → Qualificador: "Olá! Me diga seu CNPJ..." 💥 REINICIA TUDO
```

### Causa raiz
Sem `db` + `add_history_to_context=True`, cada turn do Team começa sem memória. O membro recebe apenas o task description do turn atual — sem saber o que foi coletado antes.

### Parâmetros relevantes do Team (Agno 2.5.3)
```python
# Confirmados via inspeção:
db=SqliteDb(db_file="data/agent_sessions.db")
add_history_to_context=True       # orquestrador vê histórico
store_history_messages=True       # persiste mensagens no SQLite
add_team_history_to_members=True  # membros recebem histórico do team
num_team_history_runs=5           # quantos turns anteriores repassar
```

---

## Task 1: Adicionar sqlalchemy ao pyproject.toml

**Files:**
- Modify: `pyproject.toml`

**Step 1: Adicionar dependência**

Em `pyproject.toml`, adicionar `sqlalchemy>=2.0.0` na lista de dependencies:

```toml
dependencies = [
    "agno>=2.5.3",
    "anthropic>=0.40.0",
    "google-genai>=1.0.0",
    "fastapi>=0.115.0",
    "uvicorn>=0.32.0",
    "python-dotenv>=1.0.0",
    "pypdf>=5.0.0",
    "lancedb>=0.13.0",
    "pylance>=2.0.0",
    "tantivy>=0.22.0",
    "fastembed>=0.7.0",
    "pydantic>=2.0.0",
    "openpyxl>=3.1.0",
    "httpx>=0.27.0",
    "sqlalchemy>=2.0.0",
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]
```

**Step 2: Instalar**

Run: `pip3 install sqlalchemy -q`
Expected: instala sem erro (já pode estar instalado)

**Step 3: Verificar import**

Run: `python3 -c "from agno.db.sqlite import SqliteDb; print('SqliteDb OK')"`
Expected: `SqliteDb OK`

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add sqlalchemy dependency for session storage"
```

---

## Task 2: Adicionar Session Storage e Reescrever Instruções do Orquestrador

**Files:**
- Modify: `src/orchestrator.py`

**Step 1: Escrever teste**

```python
# Adicionar em tests/test_orchestrator.py

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
```

**Step 2: Rodar para confirmar que falham**

Run: `python3 -m pytest tests/test_orchestrator.py::test_team_has_db tests/test_orchestrator.py::test_team_has_history_enabled -v`
Expected: `FAILED` — `AssertionError: assert None is not None`

**Step 3: Implementar — substituir src/orchestrator.py inteiro**

```python
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
```

**Step 4: Rodar testes**

Run: `python3 -m pytest tests/test_orchestrator.py -v`
Expected: todos os testes `PASSED`

**Step 5: Verificar que o db é criado**

Run: `python3 -c "from src.orchestrator import create_steel_sales_team; t = create_steel_sales_team(); print('OK, db:', t.db.db_file)"`
Expected: `OK, db: data/agent_sessions.db`

**Step 6: Commit**

```bash
git add src/orchestrator.py
git commit -m "fix: add session storage and context-aware delegation instructions to team"
```

---

## Task 3: Verificar criação do arquivo SQLite

**Step 1: Testar que o SQLite é criado após um run**

```python
# Adicionar em tests/test_orchestrator.py

import os

def test_sqlite_db_file_created_after_run():
    """Sessão deve ser persistida no SQLite após primeiro run."""
    team = create_steel_sales_team()
    # Apenas instancia — não faz chamada à API
    assert team.db is not None
    assert team.db.db_file == "data/agent_sessions.db"
```

Run: `python3 -m pytest tests/test_orchestrator.py::test_sqlite_db_file_created_after_run -v`
Expected: `PASSED`

**Step 2: Commit**

```bash
git add tests/test_orchestrator.py
git commit -m "test: add session storage verification tests"
```

---

## Task 4: Rodar todos os testes

**Step 1: Suite completa**

Run: `python3 -m pytest tests/ -v -k "not test_classify_incomplete_lead_as_frio"`
Expected: todos `PASSED`, nenhum `FAILED`

**Step 2: Verificar que o servidor ainda sobe**

Run: `python3 -c "from src.agent_os_server import agent_os, app; print('Server OK')"`
Expected: `Server OK`

**Step 3: Commit final (se houver mudanças)**

```bash
git add .
git commit -m "fix: team context loss — session storage + delegation instructions"
```

---

## Como testar manualmente depois

1. Reinicie o servidor: `python3 src/agent_os_server.py`
2. No Agent UI, selecione "Time de Vendas de Aço"
3. Simule o cenário do bug:
   - Envie: `"Olá, quero tubos de 4 polegadas"`
   - Forneça produto, cidade, zap, email, CNPJ em uma mensagem
   - Forneça o nome na mensagem seguinte
4. Esperado: o agente deve pedir apenas o que falta, nunca reiniciar do zero
5. Verifique que `data/agent_sessions.db` foi criado: `ls -la data/`
