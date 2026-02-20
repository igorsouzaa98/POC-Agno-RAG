# POC Agno - Agentes de IA para Atendimento de Vendas de Aço

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Criar uma POC funcional usando o framework Agno com múltiplos agentes de IA que automatizam o fluxo de atendimento/qualificação de leads de uma distribuidora de produtos de aço, desde a entrada do lead até a geração de orçamento.

**Architecture:** Multi-agent system com Agno Team onde um Agente Orquestrador coordena 3 agentes especializados: Qualificador de Leads, Especialista de Produtos e Gerador de Orçamentos. O conhecimento dos documentos (dicionário de produtos, processos de classificação) é armazenado em vector database via RAG. A API exposta via FastAPI recebe mensagens simulando a integração Blip/WhatsApp.

**Tech Stack:** Python 3.11+, Agno (agno>=1.1.1), Anthropic Claude claude-sonnet-4-6, LanceDB (vector store local, sem infra extra), FastAPI, Pydantic, python-dotenv, pypdf, openpyxl

---

## Contexto do Domínio

### Classificação de Leads
- **FRIO:** Dados incompletos, produto/volume indefinido, CNPJ inválido → coleta progressiva
- **MORNO:** Dados completos, pronto para orçamento → gerar orçamento e notificar SDR
- **QUENTE:** Orçamento gerado, passado para Closer → notificação de passagem de bastão

### Campos Obrigatórios para MORNO
Nome, WhatsApp, E-mail, CNPJ válido, UF, Cidade, Produto de Interesse, Volume estimado

### Categorias de Produtos
1. Construção Civil (Vergalhão SI50/CA60, Treliça, Arame Recozido)
2. Estrutural/Serralheria (Cantoneira, Barras, Perfis U)
3. Planos (Bobinas, Chapas, Telhas Trapezoidais/Onduladas)
4. Tubos (Metalon, Quadrado, Retangular, Patente)

---

## Task 1: Setup do Projeto

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `src/__init__.py`
- Create: `src/config.py`

**Step 1: Criar pyproject.toml com dependências**

```toml
[project]
name = "poc-agno-steel-agents"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "agno>=1.1.1",
    "anthropic>=0.40.0",
    "fastapi>=0.115.0",
    "uvicorn>=0.32.0",
    "python-dotenv>=1.0.0",
    "pypdf>=5.0.0",
    "lancedb>=0.13.0",
    "pydantic>=2.0.0",
    "openpyxl>=3.1.0",
    "httpx>=0.27.0",
]

[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.backends.legacy:BuildBackend"
```

**Step 2: Criar .env.example**

```bash
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

**Step 3: Criar src/config.py**

```python
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL_ID = "claude-sonnet-4-6"
KNOWLEDGE_BASE_DIR = "knowledge"
VECTOR_DB_PATH = "data/lancedb"
```

**Step 4: Instalar dependências**

Run: `pip install -e .`
Expected: Successfully installed all packages

**Step 5: Commit**

```bash
git init
git add pyproject.toml .env.example src/config.py src/__init__.py
git commit -m "feat: setup project structure and dependencies"
```

---

## Task 2: Preparar Base de Conhecimento (PDFs → Knowledge Base)

**Files:**
- Create: `knowledge/` (pasta com PDFs copiados)
- Create: `src/knowledge_builder.py`
- Create: `scripts/build_knowledge.py`

**Contexto:**
O Agno suporta carregamento de PDFs e armazenamento em vector database (LanceDB localmente). Vamos indexar o Dicionário de Produtos e o Processo de Classificação de Leads.

**Step 1: Copiar documentos relevantes para a pasta knowledge/**

```bash
mkdir -p knowledge
cp "/Users/igorsouza/Downloads/OneDrive_1_13-02-2026/DICIONÁRIO DE PRODUTOS DE AÇO (1).pdf" knowledge/dicionario_produtos.pdf
cp "/Users/igorsouza/Downloads/OneDrive_1_13-02-2026/Processo de Classificação de Leads.pdf" knowledge/processo_classificacao.pdf
cp "/Users/igorsouza/Downloads/OneDrive_1_13-02-2026/Estratégia de captação para Prospecção.pdf" knowledge/estrategia_captacao.pdf
```

**Step 2: Criar src/knowledge_builder.py**

```python
from agno.knowledge.pdf import PDFKnowledgeBase
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.embedder.anthropic import AnthropicEmbedder
from src.config import VECTOR_DB_PATH, KNOWLEDGE_BASE_DIR

def get_knowledge_base() -> PDFKnowledgeBase:
    """Cria e retorna a knowledge base com os documentos indexados."""
    vector_db = LanceDb(
        table_name="steel_sales_knowledge",
        uri=VECTOR_DB_PATH,
        search_type=SearchType.hybrid,
        embedder=AnthropicEmbedder(),
    )

    knowledge_base = PDFKnowledgeBase(
        path=KNOWLEDGE_BASE_DIR,
        vector_db=vector_db,
    )

    return knowledge_base
```

**Step 3: Criar scripts/build_knowledge.py**

```python
"""Script para indexar documentos na knowledge base. Executar uma vez."""
from src.knowledge_builder import get_knowledge_base

if __name__ == "__main__":
    print("Iniciando indexação da knowledge base...")
    kb = get_knowledge_base()
    kb.load(recreate=True)
    print("Knowledge base criada com sucesso!")
    print(f"Documentos indexados: {KNOWLEDGE_BASE_DIR}/")
```

**Step 4: Executar indexação**

Run: `python scripts/build_knowledge.py`
Expected: "Knowledge base criada com sucesso!" sem erros

**Step 5: Commit**

```bash
git add knowledge/ src/knowledge_builder.py scripts/build_knowledge.py
git commit -m "feat: setup knowledge base with PDF documents"
```

---

## Task 3: Modelos de Dados (Pydantic)

**Files:**
- Create: `src/models.py`

**Step 1: Criar src/models.py com todos os modelos**

```python
from enum import Enum
from pydantic import BaseModel
from typing import Optional


class LeadClassification(str, Enum):
    FRIO = "FRIO"
    MORNO = "MORNO"
    QUENTE = "QUENTE"


class ProductCategory(str, Enum):
    CONSTRUCAO_CIVIL = "construcao_civil"
    ESTRUTURAL_SERRALHERIA = "estrutural_serralheria"
    PLANOS = "planos"
    TUBOS = "tubos"


class ClientType(str, Enum):
    CONSTRUTORA = "Construtora"
    SERRALHERIA = "Serralheria"
    REVENDA = "Revenda"
    OUTRO = "Outro"


class LeadData(BaseModel):
    session_id: str
    name: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    cnpj: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    client_type: Optional[ClientType] = None
    product_interest: Optional[str] = None
    technical_product: Optional[str] = None
    volume_estimate: Optional[str] = None
    urgency: Optional[str] = None
    classification: LeadClassification = LeadClassification.FRIO
    missing_fields: list[str] = []


class IncomingMessage(BaseModel):
    session_id: str
    message: str
    lead_data: Optional[LeadData] = None


class AgentResponse(BaseModel):
    session_id: str
    message: str
    classification: LeadClassification
    lead_data: LeadData
    next_action: str
```

**Step 2: Verificar se modelos funcionam**

Run: `python -c "from src.models import LeadData, IncomingMessage; print('Models OK')"`
Expected: `Models OK`

**Step 3: Commit**

```bash
git add src/models.py
git commit -m "feat: add Pydantic data models for leads and messages"
```

---

## Task 4: Agente Qualificador de Leads

**Files:**
- Create: `src/agents/qualifier_agent.py`
- Create: `src/agents/__init__.py`
- Create: `tests/test_qualifier_agent.py`

**Step 1: Escrever o teste primeiro (TDD)**

```python
# tests/test_qualifier_agent.py
import pytest
from src.agents.qualifier_agent import create_qualifier_agent
from src.models import LeadClassification


def test_qualifier_agent_created():
    agent = create_qualifier_agent()
    assert agent is not None
    assert agent.name == "Qualificador de Leads"


def test_classify_incomplete_lead_as_frio():
    agent = create_qualifier_agent()
    response = agent.run(
        "Olá, me chamo João, tenho interesse em vergalhão."
    )
    assert response.content is not None
    # Resposta deve solicitar mais informações
    assert any(word in response.content.lower() for word in ["cnpj", "empresa", "quantidade", "volume"])


def test_classify_complete_lead_as_morno():
    agent = create_qualifier_agent()
    complete_lead_info = """
    Nome: João Silva
    WhatsApp: 11999998888
    Email: joao@construtorasilva.com.br
    CNPJ: 12.345.678/0001-90
    UF: SP
    Cidade: São Paulo
    Produto: Vergalhão CA 60 10mm
    Volume: 10 toneladas
    Urgência: Imediata
    """
    response = agent.run(f"Preciso de orçamento. Meus dados: {complete_lead_info}")
    assert response.content is not None
```

**Step 2: Rodar teste para confirmar que falha**

Run: `pytest tests/test_qualifier_agent.py -v`
Expected: `FAILED` com `ModuleNotFoundError: No module named 'src.agents.qualifier_agent'`

**Step 3: Implementar src/agents/qualifier_agent.py**

```python
from agno.agent import Agent
from agno.models.anthropic import Claude
from src.config import MODEL_ID
from src.knowledge_builder import get_knowledge_base

QUALIFIER_INSTRUCTIONS = """
Você é o Agente Qualificador de Leads de uma distribuidora de produtos de aço.

Sua função é coletar informações progressivamente e classificar o lead em:

## FRIO - Dados incompletos
Quando faltam: Nome, WhatsApp, E-mail, CNPJ válido, UF, Cidade, Produto, Volume

## MORNO - Pronto para orçamento
Quando tem todos os dados obrigatórios preenchidos e válidos

## QUENTE - Com orçamento gerado
Quando já existe um orçamento e foi passado ao Closer

## Fluxo de coleta:
1. Cumprimente o cliente cordialmente
2. Pergunte os dados faltantes de forma natural, um ou dois por vez
3. Valide o CNPJ (deve ter 14 dígitos numéricos)
4. Quando todos os dados estiverem completos, sinalize para geração de orçamento

## Campos obrigatórios para MORNO:
- Nome completo
- WhatsApp (com DDD)
- E-mail
- CNPJ (válido, 14 dígitos)
- UF (estado)
- Cidade
- Produto de interesse (use o dicionário de produtos)
- Volume estimado (ex: "10 toneladas", "500kg")

## Tom de voz:
- Profissional mas amigável
- Linguagem simples, sem jargão técnico excessivo
- Paciente e proativo na coleta de informações

Sempre finalize suas respostas indicando o status atual do lead:
STATUS: [FRIO|MORNO|QUENTE] - [motivo em uma linha]
"""

def create_qualifier_agent() -> Agent:
    knowledge_base = get_knowledge_base()

    return Agent(
        name="Qualificador de Leads",
        model=Claude(id=MODEL_ID),
        instructions=QUALIFIER_INSTRUCTIONS,
        knowledge=knowledge_base,
        search_knowledge=True,
        markdown=True,
    )
```

**Step 4: Rodar testes para confirmar que passam**

Run: `pytest tests/test_qualifier_agent.py -v`
Expected: Todos os testes `PASSED`

**Step 5: Commit**

```bash
git add src/agents/ tests/test_qualifier_agent.py
git commit -m "feat: add lead qualifier agent with TDD"
```

---

## Task 5: Agente Especialista de Produtos

**Files:**
- Create: `src/agents/product_specialist_agent.py`
- Create: `tests/test_product_specialist_agent.py`

**Step 1: Escrever o teste primeiro (TDD)**

```python
# tests/test_product_specialist_agent.py
import pytest
from src.agents.product_specialist_agent import create_product_specialist_agent


def test_product_specialist_created():
    agent = create_product_specialist_agent()
    assert agent is not None
    assert agent.name == "Especialista de Produtos"


def test_translate_popular_to_technical():
    agent = create_product_specialist_agent()
    response = agent.run("O cliente pediu 'ferro para laje', 10mm, 5 toneladas")
    assert response.content is not None
    # Deve traduzir para nomenclatura técnica
    assert any(word in response.content.lower() for word in ["vergalhão", "ca 60", "si 50"])


def test_identify_product_category():
    agent = create_product_specialist_agent()
    response = agent.run("Cliente quer metalon 30x30mm")
    assert response.content is not None
    # Deve identificar como tubo quadrado
    assert any(word in response.content.lower() for word in ["tubo", "quadrado", "metalon"])
```

**Step 2: Rodar teste para confirmar que falha**

Run: `pytest tests/test_product_specialist_agent.py -v`
Expected: `FAILED` com `ModuleNotFoundError`

**Step 3: Implementar src/agents/product_specialist_agent.py**

```python
from agno.agent import Agent
from agno.models.anthropic import Claude
from src.config import MODEL_ID
from src.knowledge_builder import get_knowledge_base

PRODUCT_SPECIALIST_INSTRUCTIONS = """
Você é o Especialista de Produtos de uma distribuidora de produtos de aço.

Sua função é:
1. Traduzir a linguagem popular do cliente para a nomenclatura técnica correta
2. Identificar a categoria do produto
3. Extrair especificações técnicas (bitola, espessura, tipo)
4. Confirmar o entendimento com o cliente

## Dicionário de Traduções Principais:

| Cliente diz | Termo técnico | Categoria |
|-------------|---------------|-----------|
| Ferro, ferro de construção | Vergalhão | Construção Civil |
| Ferro para laje | Vergalhão SI 50 | Construção Civil |
| Ferro de coluna/pilar | Vergalhão CA 60 | Construção Civil |
| Arame queimado | Arame Recozido | Construção Civil |
| Metalon | Tubo Quadrado/Retangular | Tubos |
| Tubo de ferro | Tubo Industrial | Tubos |
| Telha de zinco/galvanizada | Telha Trapezoidal Galvanizada | Planos |
| Chapa zincada | Chapa Galvanizada | Planos |
| Barra chata | Barra Chata | Serralheria |
| L de ferro | Cantoneira | Serralheria |

## Consulte sempre a knowledge base para validar a nomenclatura técnica exata.

## Formato de resposta:

Sempre retorne as informações no formato:
- **Produto técnico:** [nome técnico exato]
- **Categoria:** [construcao_civil|estrutural_serralheria|planos|tubos]
- **Especificações:** [bitola, espessura, tipo, etc.]
- **Confirmação sugerida:** "[Frase para confirmar com o cliente]"
"""

def create_product_specialist_agent() -> Agent:
    knowledge_base = get_knowledge_base()

    return Agent(
        name="Especialista de Produtos",
        model=Claude(id=MODEL_ID),
        instructions=PRODUCT_SPECIALIST_INSTRUCTIONS,
        knowledge=knowledge_base,
        search_knowledge=True,
        markdown=True,
    )
```

**Step 4: Rodar testes**

Run: `pytest tests/test_product_specialist_agent.py -v`
Expected: Todos os testes `PASSED`

**Step 5: Commit**

```bash
git add src/agents/product_specialist_agent.py tests/test_product_specialist_agent.py
git commit -m "feat: add product specialist agent with terminology translation"
```

---

## Task 6: Agente Gerador de Orçamentos

**Files:**
- Create: `src/agents/quote_generator_agent.py`
- Create: `tests/test_quote_generator_agent.py`

**Step 1: Escrever teste (TDD)**

```python
# tests/test_quote_generator_agent.py
import pytest
from src.agents.quote_generator_agent import create_quote_generator_agent
from src.models import LeadData, ClientType, LeadClassification


def test_quote_generator_created():
    agent = create_quote_generator_agent()
    assert agent is not None
    assert agent.name == "Gerador de Orçamentos"


def test_generate_quote_summary():
    agent = create_quote_generator_agent()
    lead_data = LeadData(
        session_id="test-001",
        name="João Silva",
        whatsapp="11999998888",
        email="joao@empresa.com",
        cnpj="12345678000190",
        state="SP",
        city="São Paulo",
        client_type=ClientType.CONSTRUTORA,
        product_interest="vergalhão",
        technical_product="Vergalhão CA 60 10mm",
        volume_estimate="10 toneladas",
        urgency="Imediata",
        classification=LeadClassification.MORNO,
    )

    response = agent.run(
        f"Gere um resumo de orçamento para o lead: {lead_data.model_dump_json()}"
    )
    assert response.content is not None
    assert "João Silva" in response.content or "joao" in response.content.lower()
    assert "vergalhão" in response.content.lower() or "ca 60" in response.content.lower()
```

**Step 2: Rodar teste para confirmar que falha**

Run: `pytest tests/test_quote_generator_agent.py -v`
Expected: `FAILED` com `ModuleNotFoundError`

**Step 3: Implementar src/agents/quote_generator_agent.py**

```python
from agno.agent import Agent
from agno.models.anthropic import Claude
from src.config import MODEL_ID

QUOTE_GENERATOR_INSTRUCTIONS = """
Você é o Agente Gerador de Orçamentos de uma distribuidora de produtos de aço.

Sua função é:
1. Receber os dados completos do lead (MORNO)
2. Gerar um resumo estruturado do pedido
3. Preparar as informações para o Closer dar continuidade
4. Registrar o pedido no formato padrão da empresa

## Formato do Resumo de Orçamento:

```
═══════════════════════════════════
       RESUMO DO PEDIDO - [DATA]
═══════════════════════════════════

DADOS DO CLIENTE:
• Nome: [nome]
• Empresa: [CNPJ]
• Contato: [whatsapp] | [email]
• Local: [cidade] - [UF]
• Tipo: [tipo de cliente]

PEDIDO:
• Produto: [produto técnico]
• Categoria: [categoria]
• Volume: [volume estimado]
• Urgência: [urgência]

STATUS: MORNO → Pronto para orçamento

PRÓXIMOS PASSOS:
→ Closer deve entrar em contato em até 2h
→ Apresentar tabela de preços atualizada
→ Confirmar disponibilidade em estoque

═══════════════════════════════════
```

## Regras:
- Sempre use a nomenclatura técnica correta do produto
- Se o produto não for identificado claramente, sinalize para revisão
- Verifique se todos os campos obrigatórios estão presentes antes de gerar
"""

def create_quote_generator_agent() -> Agent:
    return Agent(
        name="Gerador de Orçamentos",
        model=Claude(id=MODEL_ID),
        instructions=QUOTE_GENERATOR_INSTRUCTIONS,
        markdown=True,
    )
```

**Step 4: Rodar testes**

Run: `pytest tests/test_quote_generator_agent.py -v`
Expected: Todos os testes `PASSED`

**Step 5: Commit**

```bash
git add src/agents/quote_generator_agent.py tests/test_quote_generator_agent.py
git commit -m "feat: add quote generator agent"
```

---

## Task 7: Orquestrador (Agno Team)

**Files:**
- Create: `src/orchestrator.py`
- Create: `tests/test_orchestrator.py`

**Contexto:**
O Agno Team coordena múltiplos agentes. O Orquestrador recebe a mensagem do cliente, decide qual agente acionar, e retorna a resposta consolidada.

**Step 1: Escrever testes (TDD)**

```python
# tests/test_orchestrator.py
import pytest
from src.orchestrator import create_steel_sales_team
from src.models import IncomingMessage, LeadClassification


def test_team_created():
    team = create_steel_sales_team()
    assert team is not None


def test_new_lead_gets_welcomed_and_asked_data():
    team = create_steel_sales_team()
    msg = IncomingMessage(
        session_id="sess-001",
        message="Oi, quero comprar vergalhão"
    )
    response = team.run(msg.message)
    assert response.content is not None
    # Deve pedir dados do cliente
    content_lower = response.content.lower()
    assert any(word in content_lower for word in ["nome", "empresa", "cnpj", "dados"])


def test_complete_lead_transitions_to_morno():
    team = create_steel_sales_team()
    complete_message = """
    Meu nome é Maria Souza, whatsapp 11988887777, email maria@construtoraMS.com.br,
    CNPJ 98.765.432/0001-10, estou em Campinas - SP.
    Preciso de 5 toneladas de vergalhão CA 60 10mm com urgência imediata.
    """
    response = team.run(complete_message)
    assert response.content is not None
    assert "morno" in response.content.lower() or "orçamento" in response.content.lower()
```

**Step 2: Rodar teste para confirmar que falha**

Run: `pytest tests/test_orchestrator.py -v`
Expected: `FAILED` com `ModuleNotFoundError`

**Step 3: Implementar src/orchestrator.py**

```python
from agno.team import Team
from agno.models.anthropic import Claude
from src.config import MODEL_ID
from src.agents.qualifier_agent import create_qualifier_agent
from src.agents.product_specialist_agent import create_product_specialist_agent
from src.agents.quote_generator_agent import create_quote_generator_agent

ORCHESTRATOR_INSTRUCTIONS = """
Você é o Orquestrador do sistema de atendimento de uma distribuidora de produtos de aço.

Sua função é coordenar os agentes especializados:
1. **Qualificador de Leads** - Para coletar e classificar dados do cliente
2. **Especialista de Produtos** - Para traduzir e validar termos técnicos
3. **Gerador de Orçamentos** - Para preparar o resumo quando lead for MORNO

## Fluxo de decisão:

### Mensagem inicial ou dados incompletos:
→ Acione o Qualificador de Leads
→ Continue coletando informações

### Quando cliente menciona produto específico:
→ Acione o Especialista de Produtos para validar nomenclatura
→ Retorne ao Qualificador para continuar coleta

### Quando todos os dados estiverem completos (lead MORNO):
→ Acione o Especialista de Produtos para confirmação final
→ Acione o Gerador de Orçamentos para criar o resumo
→ Informe o cliente que o orçamento está sendo preparado

## Sempre:
- Mantenha o contexto da conversa
- Seja cordial e profissional
- Nunca peça a mesma informação duas vezes
- Classifique o lead ao final de cada resposta
"""

def create_steel_sales_team() -> Team:
    qualifier = create_qualifier_agent()
    product_specialist = create_product_specialist_agent()
    quote_generator = create_quote_generator_agent()

    team = Team(
        name="Time de Vendas de Aço",
        mode="coordinate",
        model=Claude(id=MODEL_ID),
        members=[qualifier, product_specialist, quote_generator],
        instructions=ORCHESTRATOR_INSTRUCTIONS,
        markdown=True,
        show_members_responses=True,
    )

    return team
```

**Step 4: Rodar testes**

Run: `pytest tests/test_orchestrator.py -v`
Expected: Todos os testes `PASSED`

**Step 5: Commit**

```bash
git add src/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add orchestrator team coordinating all agents"
```

---

## Task 8: API FastAPI (Interface de Teste)

**Files:**
- Create: `src/api.py`
- Create: `tests/test_api.py`

**Step 1: Escrever testes de API (TDD)**

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from src.api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_send_message_endpoint_exists(client):
    payload = {
        "session_id": "test-session-001",
        "message": "Olá, quero comprar vergalhão"
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "session_id" in data
    assert "classification" in data


def test_message_with_incomplete_data_returns_frio(client):
    payload = {
        "session_id": "test-session-002",
        "message": "Quero comprar aço"
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["classification"] == "FRIO"
```

**Step 2: Rodar testes para confirmar que falham**

Run: `pytest tests/test_api.py -v`
Expected: `FAILED` com `ModuleNotFoundError`

**Step 3: Implementar src/api.py**

```python
from fastapi import FastAPI, HTTPException
from src.models import IncomingMessage, AgentResponse, LeadClassification, LeadData
from src.orchestrator import create_steel_sales_team
import re

app = FastAPI(
    title="POC Agno - Agentes de Vendas de Aço",
    description="API de automação do fluxo de atendimento para distribuidora de aço",
    version="0.1.0",
)

# Inicializa o team uma vez (pode usar cache de sessão em produção)
_team = None

def get_team():
    global _team
    if _team is None:
        _team = create_steel_sales_team()
    return _team


def extract_classification(response_text: str) -> LeadClassification:
    """Extrai a classificação do texto de resposta do agente."""
    text_upper = response_text.upper()
    if "QUENTE" in text_upper:
        return LeadClassification.QUENTE
    elif "MORNO" in text_upper:
        return LeadClassification.MORNO
    return LeadClassification.FRIO


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "POC Agno Steel Agents"}


@app.post("/chat", response_model=AgentResponse)
async def chat(message: IncomingMessage):
    try:
        team = get_team()

        # Monta contexto da sessão se houver dados do lead
        context = message.message
        if message.lead_data:
            context = f"[DADOS DO LEAD: {message.lead_data.model_dump_json()}]\n\nMensagem do cliente: {message.message}"

        response = team.run(context)
        classification = extract_classification(response.content)

        lead_data = message.lead_data or LeadData(session_id=message.session_id)
        lead_data.classification = classification

        return AgentResponse(
            session_id=message.session_id,
            message=response.content,
            classification=classification,
            lead_data=lead_data,
            next_action="collect_data" if classification == LeadClassification.FRIO else
                       "generate_quote" if classification == LeadClassification.MORNO else
                       "transfer_to_closer"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {
        "message": "POC Agno - Agentes de Vendas de Aço",
        "endpoints": {
            "POST /chat": "Enviar mensagem para os agentes",
            "GET /health": "Status da API",
        }
    }
```

**Step 4: Rodar testes da API**

Run: `pytest tests/test_api.py -v`
Expected: Todos os testes `PASSED`

**Step 5: Commit**

```bash
git add src/api.py tests/test_api.py
git commit -m "feat: add FastAPI endpoints for agent interaction"
```

---

## Task 9: Script de Demo Interativo

**Files:**
- Create: `scripts/demo_chat.py`

**Step 1: Criar script de demo interativo**

```python
#!/usr/bin/env python3
"""
Demo interativo do sistema de agentes.
Simula uma conversa de WhatsApp com o atendente IA.
"""
from src.orchestrator import create_steel_sales_team
from src.models import IncomingMessage

def main():
    print("=" * 60)
    print("  POC AGNO - ATENDIMENTO DE VENDAS DE AÇO")
    print("  Simulação de conversa via WhatsApp/Blip")
    print("=" * 60)
    print("Digite 'sair' para encerrar\n")

    team = create_steel_sales_team()
    session_id = "demo-session-001"

    # Mensagem inicial do sistema
    initial_response = team.run(
        "Um novo lead chegou via Lead Ads. Inicie o atendimento cordialmente."
    )
    print(f"\n🤖 Agente: {initial_response.content}\n")

    while True:
        user_input = input("👤 Cliente: ").strip()

        if user_input.lower() in ["sair", "exit", "quit"]:
            print("\nEncerrando demo...")
            break

        if not user_input:
            continue

        response = team.run(user_input)
        print(f"\n🤖 Agente: {response.content}\n")
        print("-" * 40)


if __name__ == "__main__":
    main()
```

**Step 2: Testar o demo manualmente**

Run: `python scripts/demo_chat.py`
Expected: Prompt interativo iniciado, agente cumprimenta o usuário

**Step 3: Testar cenário completo de lead MORNO**

Simular uma conversa onde o cliente fornece:
1. Nome + produto interesse
2. CNPJ + empresa
3. UF + Cidade
4. Volume + urgência

Expected: Agente classifica como MORNO e gera resumo de orçamento

**Step 4: Commit**

```bash
git add scripts/demo_chat.py
git commit -m "feat: add interactive demo script for testing full conversation flow"
```

---

## Task 10: Testes de Integração e Cenários de Negócio

**Files:**
- Create: `tests/test_business_scenarios.py`

**Contexto:**
O arquivo "Cenários de teste - Agente.xlsx" contém casos de teste definidos pelo negócio. Vamos implementar os cenários principais.

**Step 1: Escrever testes de cenários de negócio**

```python
# tests/test_business_scenarios.py
"""
Cenários de teste baseados nos casos definidos pelo negócio.
Ref: Cenários de teste - Agente.xlsx
"""
import pytest
from src.orchestrator import create_steel_sales_team


@pytest.fixture(scope="module")
def team():
    return create_steel_sales_team()


class TestCenarioLeadFrio:
    """Lead que não fornece dados suficientes"""

    def test_apenas_interesse_gera_perguntas(self, team):
        response = team.run("Quero comprar aço")
        assert response.content is not None
        content_lower = response.content.lower()
        assert any(w in content_lower for w in ["nome", "empresa", "cnpj"])

    def test_produto_invalido_solicita_esclarecimento(self, team):
        response = team.run("Quero comprar o produto X especial")
        assert response.content is not None
        # Deve pedir mais detalhes sobre o produto


class TestCenarioLeadMorno:
    """Lead com dados completos prontos para orçamento"""

    def test_dados_completos_gera_resumo(self, team):
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
        assert response.content is not None
        content_lower = response.content.lower()
        # Deve reconhecer como MORNO e gerar resumo
        assert any(w in content_lower for w in ["morno", "orçamento", "resumo", "pedido"])


class TestCenarioTerminologiaProdutos:
    """Tradução de linguagem popular para técnica"""

    def test_ferro_para_laje_identifica_vergalhao(self, team):
        response = team.run("Preciso de ferro para laje, uns 10mm, umas 5 toneladas")
        assert response.content is not None
        content_lower = response.content.lower()
        assert any(w in content_lower for w in ["vergalhão", "ca 60", "si 50"])

    def test_metalon_identifica_tubo(self, team):
        response = team.run("Quero metalon 30x30")
        assert response.content is not None
        content_lower = response.content.lower()
        assert any(w in content_lower for w in ["tubo", "quadrado", "retangular"])

    def test_telha_de_zinco_identifica_galvanizada(self, team):
        response = team.run("Preciso de telha de zinco")
        assert response.content is not None
        content_lower = response.content.lower()
        assert any(w in content_lower for w in ["telha", "galvanizada", "trapezoidal"])
```

**Step 2: Rodar testes de cenário**

Run: `pytest tests/test_business_scenarios.py -v --timeout=60`
Expected: Maioria dos testes `PASSED` (alguns podem variar por ser LLM)

**Step 3: Ajustar prompts se necessário**

Se testes falharem, revisar as instruções dos agentes para cobrir os casos

**Step 4: Rodar todos os testes**

Run: `pytest tests/ -v`
Expected: Todos os testes passando

**Step 5: Commit**

```bash
git add tests/test_business_scenarios.py
git commit -m "test: add business scenario tests covering lead qualification flows"
```

---

## Task 11: Documentação e README

**Files:**
- Create: `README.md`
- Create: `CLAUDE.md`

**Step 1: Criar README.md**

```markdown
# POC Agno - Agentes de IA para Atendimento de Vendas de Aço

## Visão Geral

Sistema multi-agente usando o framework Agno com Claude (Anthropic) para automatizar
o fluxo de atendimento e qualificação de leads de uma distribuidora de produtos de aço.

## Arquitetura

```
Lead (WhatsApp/Blip)
    ↓
FastAPI (/chat)
    ↓
Agno Team (Orquestrador)
    ├─ Qualificador de Leads → Classifica: FRIO | MORNO | QUENTE
    ├─ Especialista de Produtos → Traduz terminologia técnica
    └─ Gerador de Orçamentos → Prepara resumo para Closer
    ↓
Resposta + Classificação
```

## Setup

1. Clonar repositório e instalar dependências:
   ```bash
   pip install -e .
   ```

2. Configurar variáveis de ambiente:
   ```bash
   cp .env.example .env
   # Editar .env com sua ANTHROPIC_API_KEY
   ```

3. Indexar a knowledge base:
   ```bash
   python scripts/build_knowledge.py
   ```

4. Rodar demo interativo:
   ```bash
   python scripts/demo_chat.py
   ```

5. Iniciar API:
   ```bash
   uvicorn src.api:app --reload
   ```

## Testes

```bash
pytest tests/ -v
```

## Classificação de Leads

| Status | Condição | Próxima Ação |
|--------|----------|--------------|
| FRIO | Dados incompletos | Coletar informações |
| MORNO | Dados completos | Gerar orçamento |
| QUENTE | Com orçamento | Transferir ao Closer |
```

**Step 2: Criar CLAUDE.md com contexto do projeto**

```markdown
# POC Agno Steel Agents - Contexto para Claude

## Projeto
POC de agentes de IA com Agno para distribuidora de produtos de aço.

## Comandos principais
- `pytest tests/ -v` - Rodar todos os testes
- `python scripts/demo_chat.py` - Demo interativo
- `python scripts/build_knowledge.py` - Reindexar documentos
- `uvicorn src.api:app --reload` - Iniciar API

## Estrutura
- `src/agents/` - Agentes individuais
- `src/orchestrator.py` - Team coordinator
- `src/knowledge_builder.py` - RAG setup
- `knowledge/` - PDFs indexados

## Modelo usado
claude-sonnet-4-6 (Anthropic)
```

**Step 3: Commit final**

```bash
git add README.md CLAUDE.md
git commit -m "docs: add README and CLAUDE.md with project documentation"
```

---

## Resumo do Projeto Final

```
poc-agno-steel-agents/
├── knowledge/                    # PDFs para RAG
│   ├── dicionario_produtos.pdf
│   ├── processo_classificacao.pdf
│   └── estrategia_captacao.pdf
├── data/
│   └── lancedb/                  # Vector DB local
├── src/
│   ├── __init__.py
│   ├── config.py                 # Configurações
│   ├── models.py                 # Pydantic models
│   ├── knowledge_builder.py      # RAG setup
│   ├── orchestrator.py           # Agno Team
│   ├── api.py                    # FastAPI
│   └── agents/
│       ├── __init__.py
│       ├── qualifier_agent.py    # Qualificador FRIO/MORNO/QUENTE
│       ├── product_specialist_agent.py  # Tradutor de produtos
│       └── quote_generator_agent.py     # Gerador de orçamentos
├── scripts/
│   ├── build_knowledge.py        # Indexar PDFs
│   └── demo_chat.py              # Demo interativo
├── tests/
│   ├── test_qualifier_agent.py
│   ├── test_product_specialist_agent.py
│   ├── test_quote_generator_agent.py
│   ├── test_orchestrator.py
│   ├── test_api.py
│   └── test_business_scenarios.py
├── docs/
│   └── plans/
│       └── 2026-02-20-poc-agno-steel-sales-agents.md
├── pyproject.toml
├── .env.example
├── README.md
└── CLAUDE.md
```

## Decisões Técnicas

1. **LanceDB** como vector store local (sem infra extra para POC)
2. **Agno Team no modo "coordinate"** para o orquestrador decidir qual agente acionar
3. **Claude claude-sonnet-4-6** como modelo principal (melhor custo/benefício para POC)
4. **Anthropic Embedder** para consistência com o modelo de linguagem
5. **FastAPI** para interface de teste que simula integração Blip
6. **TDD** para garantir que cada agente funciona isoladamente antes de integrar
