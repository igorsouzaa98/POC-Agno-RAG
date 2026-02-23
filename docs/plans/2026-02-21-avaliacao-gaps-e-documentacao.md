# Avaliação de Gaps, Documentação e Escalabilidade

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Avaliar o projeto atual contra as expectativas do cliente (Aço Cearense), gerar documentação técnica completa de cada arquivo, e implementar os gaps de funcionalidade identificados.

**Architecture:** O projeto já possui uma base sólida com 3 agentes Agno especializados (Qualificador, Especialista de Produtos, Gerador de Orçamentos) coordenados por um Team em modo "coordinate", com RAG via LanceDB+FastEmbed e API FastAPI. Os gaps principais são: scoring numérico, regras de desqualificação automática, follow-up cadenciado pós-orçamento, integração CRM (Salesforce), e transbordo humanizado.

**Tech Stack:** Python 3.11+, Agno 2.5.3, FastAPI, LanceDB, FastEmbed (local embeddings), SQLite (sessões), APScheduler (follow-up), pytest

---

## GAP ANALYSIS — Projeto Atual vs Expectativas do Cliente

### ✅ O que o projeto JÁ FAZ

| Expectativa | Status | Onde está implementado |
|-------------|--------|----------------------|
| Qualificação de leads (FRIO/MORNO/QUENTE) | ✅ Implementado | `src/agents/qualifier_agent.py` |
| Tradução linguagem popular → técnica | ✅ Implementado | `src/agents/product_specialist_agent.py` |
| Coleta de dados obrigatórios (CNPJ, UF, volume) | ✅ Implementado | `src/agents/qualifier_agent.py` |
| Geração de resumo de pedido | ✅ Implementado | `src/agents/quote_generator_agent.py` |
| Persistência de sessão (memória multi-turno) | ✅ Implementado | `src/orchestrator.py` (SQLiteDb) |
| API REST para integração | ✅ Implementado | `src/api.py` |
| Knowledge base com PDFs | ✅ Implementado | `src/knowledge_builder.py` |
| UI de teste (AgentOS) | ✅ Implementado | `src/agent_os_server.py` |

### ❌ O que FALTA implementar

| Expectativa | Status | Prioridade |
|-------------|--------|------------|
| **Scoring numérico por volume/tonelagem** | ❌ Ausente | Alta |
| **Regras de desqualificação automática** (PF, fora CE, produto indisponível, volume mínimo) | ❌ Ausente | Alta |
| **Follow-up cadenciado pós-orçamento** (2h, 10h, 20h, 48h) | ❌ Ausente | Média |
| **Transbordo humanizado** (3 respostas incoerentes, pedido explícito de humano) | ❌ Ausente | Alta |
| **Integração CRM Salesforce** (atualizar status do lead) | ❌ Ausente | Média |
| **Webhook WhatsApp/Blip** (entrada de mensagens real) | ❌ Ausente | Média |

---

## DOCUMENTAÇÃO TÉCNICA COMPLETA

---

### Task 1: Criar arquivo ARCHITECTURE.md

**Files:**
- Create: `docs/ARCHITECTURE.md`

**Step 1: Escrever documentação completa de cada arquivo**

Conteúdo completo a escrever em `docs/ARCHITECTURE.md`:

```markdown
# Documentação Técnica — POC Agno Steel Agents

## Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        ENTRADA DO LEAD                          │
│         (WhatsApp / Blip / API REST / Demo CLI)                 │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   src/api.py (FastAPI)                          │
│  POST /chat  →  recebe mensagem, chama orquestrador             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              src/orchestrator.py (Agno Team)                    │
│  mode="coordinate" → decide qual agente acionar                 │
│  SQLite (data/agent_sessions.db) → persiste histórico           │
└──────┬─────────────────┬────────────────────┬───────────────────┘
       │                 │                    │
       ▼                 ▼                    ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐
│  Qualificador│ │ Especialista │ │ Gerador de Orçamentos │
│  de Leads    │ │ de Produtos  │ │                      │
│              │ │              │ │                      │
│ Coleta dados │ │ Traduz termos│ │ Gera resumo para     │
│ Classifica   │ │ populares →  │ │ o Closer             │
│ FRIO/MORNO/  │ │ técnicos     │ │                      │
│ QUENTE       │ │              │ │                      │
└──────┬───────┘ └──────┬───────┘ └──────────┬───────────┘
       │                │                    │
       └────────────────┴────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                 src/knowledge_builder.py                        │
│  FastEmbed (local) → embeddings → LanceDB (vector search)      │
│  PDFs: dicionario_produtos, processo_classificacao,            │
│        estrategia_captacao                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Arquivos do Projeto

### `src/config.py`
**O que faz:** Carrega variáveis de ambiente e fornece a função `get_model()` que retorna o modelo de IA correto (Gemini ou Claude) baseado no `MODEL_ID` configurado no `.env`.

**Funções:**
- `get_model() → Agent model`: Lê `MODEL_ID` do `.env`. Se começa com "gemini", retorna `Gemini(id=...)`. Caso contrário, retorna `Claude(id=...)`. Permite trocar de modelo sem alterar código.

**Variáveis exportadas:**
- `GOOGLE_API_KEY` — chave da API Google (para Gemini)
- `ANTHROPIC_API_KEY` — chave da API Anthropic (para Claude)
- `MODEL_ID` — ID do modelo (padrão: `gemini-2.5-flash-preview-04-17`)
- `KNOWLEDGE_BASE_DIR` — pasta dos PDFs (`knowledge/`)
- `VECTOR_DB_PATH` — pasta do banco vetorial (`data/lancedb`)

**Como manter:** Para trocar de modelo, mude apenas `MODEL_ID` no `.env`. Para adicionar novos provedores de IA (OpenAI, etc.), adicione um `elif` na função `get_model()`.

---

### `src/models.py`
**O que faz:** Define todos os modelos de dados (Pydantic) usados na API e internamente pelos agentes.

**Classes:**

- **`LeadClassification` (Enum):** Os 3 estados possíveis de um lead:
  - `FRIO` — dados incompletos, lead não qualificado
  - `MORNO` — dados completos, pronto para receber orçamento humano
  - `QUENTE` — orçamento já gerado, passou para o Closer

- **`ProductCategory` (Enum):** Categorias de produtos que a empresa vende: `CONSTRUCAO_CIVIL`, `ESTRUTURAL_SERRALHERIA`, `PLANOS`, `TUBOS`.

- **`ClientType` (Enum):** Tipos de cliente: `CONSTRUTORA`, `SERRALHERIA`, `REVENDA`, `OUTRO`.

- **`LeadData` (BaseModel):** O "perfil" completo do lead. Campos:
  - `session_id` — ID único da conversa
  - `name`, `whatsapp`, `email`, `cnpj` — dados de contato
  - `state`, `city` — localização
  - `client_type` — tipo de empresa
  - `product_interest` — como o cliente descreveu o produto
  - `technical_product` — nome técnico traduzido pelo Especialista
  - `volume_estimate` — quantidade desejada (ex: "10 toneladas")
  - `urgency` — prazo do cliente
  - `classification` — FRIO/MORNO/QUENTE (padrão: FRIO)
  - `missing_fields` — lista de campos ainda faltantes

- **`IncomingMessage` (BaseModel):** Payload do POST /chat. Contém `session_id`, `message` (texto do cliente) e opcionalmente `lead_data` (estado anterior).

- **`AgentResponse` (BaseModel):** Resposta do POST /chat. Contém `session_id`, `message` (resposta do agente), `classification`, `lead_data` atualizado e `next_action` (o que o sistema deve fazer a seguir).

**Como manter:** Para adicionar campos ao lead, adicione em `LeadData`. Para novos estados, adicione no Enum correspondente. Todos os modelos usam Pydantic v2 com validação automática.

---

### `src/knowledge_builder.py`
**O que faz:** Configura e carrega a base de conhecimento RAG (Retrieval-Augmented Generation) com os PDFs da empresa.

**Funções:**

- **`get_knowledge_base() → Knowledge`:** Cria e retorna um objeto `Knowledge` do Agno configurado com:
  - **Embedder:** `FastEmbedEmbedder` com modelo `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensões). Roda localmente sem API key. Suporta português.
  - **Vector DB:** `LanceDb` em `data/lancedb/` com busca híbrida (vetorial + palavra-chave).
  - **Reader:** `PDFReader` com divisão por página e sanitização de conteúdo.
  - `max_results=5` — retorna até 5 trechos relevantes por busca.

- **`load_knowledge_base(recreate=False) → Knowledge`:** Usado pelo script `scripts/build_knowledge.py`. Indexa todos os PDFs da pasta `knowledge/`. Se `recreate=True`, apaga e recria o índice (use ao atualizar os PDFs).

**PDFs indexados:**
- `dicionario_produtos.pdf` — catálogo com nomes técnicos, bitolas, especificações
- `processo_classificacao.pdf` — regras de qualificação de leads
- `estrategia_captacao.pdf` — estratégia de prospecção da empresa

**Como manter:** Para adicionar novos documentos, coloque o PDF na pasta `knowledge/` e rode `python scripts/build_knowledge.py`. Para atualizar um PDF existente, rode com `recreate=True`.

---

### `src/orchestrator.py`
**O que faz:** Cria e configura o "Time de Vendas" — um `Team` do Agno no modo `coordinate` que orquestra os 3 agentes especializados.

**Como funciona o modo `coordinate`:** O Team (orquestrador) recebe cada mensagem do cliente, decide qual agente acionar, passa a tarefa com contexto completo, recebe a resposta e retorna ao usuário. O orquestrador é o "guardião" do estado da conversa.

**Configurações importantes:**
- `db=SqliteDb(db_file="data/agent_sessions.db")` — persiste histórico em SQLite
- `add_history_to_context=True` — inclui histórico no contexto do orquestrador
- `store_history_messages=True` — salva mensagens no banco
- `add_team_history_to_members=True` — agentes membros também recebem histórico
- `num_team_history_runs=5` — mantém os últimos 5 turnos no contexto

**`ORCHESTRATOR_INSTRUCTIONS`:** As instruções críticas do orquestrador. Define:
1. Que o orquestrador DEVE incluir um bloco `---CONTEXTO ACUMULADO---` em CADA delegação (porque os agentes membros não têm memória própria)
2. O fluxo de decisão: incompleto → Qualificador; produto mencionado → Especialista; dados completos → Gerador
3. Regras para não repetir perguntas e não reiniciar a conversa

**`create_steel_sales_team() → Team`:** Factory function que instancia os 3 agentes e o Team. Use sempre esta função para criar o time.

**Como manter:** Se adicionar um 4º agente, importe e instancie aqui, adicione em `members=[]` e atualize as instruções do orquestrador. O bloco de contexto acumulado é crítico — nunca remova essa instrução.

---

### `src/agents/qualifier_agent.py`
**O que faz:** Agente responsável por coletar os dados obrigatórios do lead e classificá-lo como FRIO, MORNO ou QUENTE.

**Lógica de classificação (via prompt):**
- **FRIO:** Falta qualquer campo obrigatório (Nome, WhatsApp, Email, CNPJ, UF, Cidade, Produto, Volume)
- **MORNO:** Todos os 8 campos obrigatórios preenchidos e válidos
- **QUENTE:** Já existe orçamento gerado e foi passado ao Closer

**Formato de resposta obrigatório:** Sempre termina com `STATUS: [FRIO|MORNO|QUENTE] - [motivo]`. A API usa esse padrão para extrair a classificação.

**`create_qualifier_agent() → Agent`:** Cria o agente com:
- `knowledge=get_knowledge_base()` — acesso ao dicionário de produtos e processos
- `search_knowledge=True` — busca automática na knowledge base
- Tom: profissional, amigável, paciente

**Como manter:** Para adicionar novos campos obrigatórios, atualize as listas em `QUALIFIER_INSTRUCTIONS`. Para mudar as regras de classificação, edite a seção correspondente no prompt.

---

### `src/agents/product_specialist_agent.py`
**O que faz:** Agente tradutor que converte a linguagem popular do cliente para a nomenclatura técnica correta usada no sistema da empresa.

**Dicionário embutido no prompt** (principais mapeamentos):
| Cliente diz | Técnico | Categoria |
|-------------|---------|-----------|
| ferro para laje | Vergalhão SI 50 | Construção Civil |
| arame queimado | Arame Recozido | Construção Civil |
| metalon | Tubo Quadrado/Retangular | Tubos |
| L de ferro | Cantoneira | Serralheria |

**Formato de resposta obrigatório:**
- `**Produto técnico:**` — nome exato
- `**Categoria:**` — enum de categoria
- `**Especificações:**` — bitola, espessura, tipo
- `**Confirmação sugerida:**` — frase para confirmar com o cliente

**`create_product_specialist_agent() → Agent`:** Cria o agente com acesso à knowledge base para validar nomes técnicos além do dicionário embutido.

**Como manter:** Para adicionar novos produtos, adicione ao dicionário no prompt E ao PDF `dicionario_produtos.pdf` (depois reindexe com `build_knowledge.py`).

---

### `src/agents/quote_generator_agent.py`
**O que faz:** Agente que gera o resumo estruturado do pedido quando o lead atingiu status MORNO (dados completos).

**Output:** Um bloco formatado com delimitadores `═══` contendo dados do cliente, detalhes do pedido, status atual e próximos passos para o Closer.

**Próximos passos gerados automaticamente:**
1. Closer deve contatar em até 2h
2. Apresentar tabela de preços
3. Confirmar disponibilidade em estoque

**`create_quote_generator_agent() → Agent`:** Cria o agente SEM knowledge base (não precisa buscar produtos, só formatar dados já validados).

**Como manter:** Para mudar o formato do resumo, edite o template em `QUOTE_GENERATOR_INSTRUCTIONS`. Para adicionar campos ao resumo, adicione na seção `PEDIDO:` do template.

---

### `src/api.py`
**O que faz:** API REST FastAPI que expõe o sistema de agentes para integração externa (WhatsApp/Blip, CRM, etc.).

**Endpoints:**

- **`GET /`** — retorna lista dos endpoints disponíveis (index)
- **`GET /health`** — health check, retorna `{"status": "ok", ...}`
- **`POST /chat`** — endpoint principal. Recebe `IncomingMessage`, processa com o Team, retorna `AgentResponse`.

**`get_team()`:** Singleton — cria o Team uma vez e reutiliza entre requisições (lazy initialization). Evita recriar o Team (e sua conexão com SQLite) a cada request.

**`extract_classification(response_text: str) → LeadClassification`:** Extrai a classificação do texto de resposta do agente. Busca pelas palavras "QUENTE" ou "MORNO" (maiúsculas) no texto. Se não encontrar nenhuma, retorna FRIO. **Atenção:** este método é frágil — depende do agente incluir a palavra no texto.

**Fluxo do POST /chat:**
1. Recebe mensagem + session_id + lead_data opcional
2. Monta contexto (inclui lead_data serializado se disponível)
3. Chama `team.run(context)` — bloqueante
4. Extrai classificação do texto de resposta
5. Define `next_action` baseado na classificação
6. Retorna `AgentResponse`

**Como manter:** Para adicionar novos endpoints (ex: webhook do Blip), adicione novas rotas aqui. Para tornar `extract_classification` mais robusto, use regex ou estruture a resposta do agente como JSON.

---

### `src/agent_os_server.py`
**O que faz:** Servidor para o Agent UI (frontend do Agno). Permite testar os agentes visualmente via browser sem precisar de Postman ou código.

**Como usar:**
1. Rodar: `python src/agent_os_server.py`
2. Em outro terminal: `npx create-agent-ui@latest`
3. Acessar `http://localhost:3001` e conectar em `http://localhost:7777`

**O que expõe no UI:**
- 3 agentes individuais (para testes isolados)
- 1 time completo (para teste end-to-end)

**Como manter:** Se adicionar novos agentes, instancie aqui e adicione na lista `agents=[]`. Apenas para desenvolvimento/demo — não use em produção.

---

### `scripts/build_knowledge.py`
**O que faz:** Script one-time para indexar os PDFs da pasta `knowledge/` no banco vetorial LanceDB.

**Quando rodar:**
- Primeira vez que clonar o projeto
- Quando adicionar novos PDFs ao `knowledge/`
- Quando modificar PDFs existentes (use `recreate=True`)

**Como rodar:** `python scripts/build_knowledge.py`

---

### `scripts/demo_chat.py`
**O que faz:** Demo interativo CLI que simula uma conversa de WhatsApp com o time de agentes. Útil para testes rápidos sem precisar da API.

**Como rodar:** `python scripts/demo_chat.py`

**Fluxo:** Cria o Team → loop de input/output até o usuário digitar "sair".

---

### `tests/`

| Arquivo | O que testa |
|---------|-------------|
| `test_qualifier_agent.py` | Criação do agente e resposta básica (requer API key) |
| `test_product_specialist_agent.py` | Criação e tradução de termos |
| `test_quote_generator_agent.py` | Criação e geração de resumo |
| `test_orchestrator.py` | Criação do Team e persistência de sessão |
| `test_api.py` | Endpoints da API |
| `test_business_scenarios.py` | Cenários reais do negócio (estruturais sem API key + integração com API key) |

**Como rodar:**
```bash
# Testes sem API key (estruturais)
pytest tests/ -v -k "not test_classify_incomplete_lead_as_frio"

# Todos os testes (requer API key configurada)
pytest tests/ -v
```

---

## Fluxo Completo de uma Conversa

```
Cliente: "Quero metalon 30x30"
    ↓
API (POST /chat)
    ↓
Orquestrador → decide: produto mencionado → Especialista de Produtos
    ↓
Especialista: "Produto: Tubo Retangular 30x30mm, Categoria: Tubos"
    ↓
Orquestrador → decide: dados incompletos → Qualificador
    ↓
Qualificador: "Ótimo! Metalon para serralheria, certo? Agora preciso de:
               - Seu nome completo
               - WhatsApp com DDD
               ... STATUS: FRIO"
    ↓
API → extrai FRIO → next_action: "collect_data"
    ↓
Cliente responde com todos os dados...
    ↓
Qualificador → STATUS: MORNO
    ↓
Orquestrador → Gerador de Orçamentos
    ↓
Gerador → Resumo formatado para o Closer
    ↓
API → MORNO → next_action: "generate_quote"
```

---

## Dados e Persistência

| Arquivo | Conteúdo | Quando é criado |
|---------|----------|-----------------|
| `data/lancedb/` | Vetores dos PDFs (embeddings) | `python scripts/build_knowledge.py` |
| `data/agent_sessions.db` | Histórico de conversas (SQLite) | Automaticamente na primeira chamada |
| `knowledge/*.pdf` | PDFs da empresa (já indexados) | Fornecidos manualmente |

---

## Variáveis de Ambiente (.env)

```env
ANTHROPIC_API_KEY=sk-ant-...    # Para usar Claude
GOOGLE_API_KEY=AIza...          # Para usar Gemini
MODEL_ID=gemini-2.5-flash-preview-04-17   # Qual modelo usar
```
```

**Step 2: Verificar se o arquivo foi criado**
```bash
ls -la docs/ARCHITECTURE.md
```

**Step 3: Commit**
```bash
git add docs/ARCHITECTURE.md
git commit -m "docs: add complete architecture documentation for all files and functions"
```

---

## IMPLEMENTAÇÃO DOS GAPS

---

### Task 2: Adicionar Score Numérico ao LeadData

**Por que:** O cliente quer priorização de leads por volume. Maior tonelagem = score mais alto = topo da fila do vendedor.

**Files:**
- Modify: `src/models.py`

**Step 1: Escrever teste de score**

Em `tests/test_business_scenarios.py`, adicionar em `TestModelos`:

```python
def test_lead_data_has_score_field(self):
    from src.models import LeadData
    lead = LeadData(session_id="test")
    assert lead.score == 0  # padrão é 0

def test_lead_score_range_is_valid(self):
    from src.models import LeadData
    lead = LeadData(session_id="test", score=85)
    assert 0 <= lead.score <= 100
```

**Step 2: Rodar e verificar que falha**
```bash
pytest tests/test_business_scenarios.py::TestModelos::test_lead_data_has_score_field -v
```
Esperado: `AttributeError: 'LeadData' object has no attribute 'score'`

**Step 3: Implementar score em LeadData**

Em `src/models.py`, adicionar campo após `missing_fields`:

```python
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
    score: int = 0                    # 0-100, maior = mais quente
    disqualified_reason: Optional[str] = None  # motivo da desqualificação automática
```

**Step 4: Rodar testes**
```bash
pytest tests/test_business_scenarios.py::TestModelos -v
```
Esperado: todos PASS

**Step 5: Commit**
```bash
git add src/models.py tests/test_business_scenarios.py
git commit -m "feat: add score and disqualified_reason fields to LeadData"
```

---

### Task 3: Criar Módulo de Regras de Negócio

**Por que:** Centralizar as regras comerciais (volume mínimo, estados atendidos, produtos disponíveis) separadas do prompt do agente para facilitar manutenção.

**Files:**
- Create: `src/business_rules.py`
- Create: `tests/test_business_rules.py`

**Step 1: Escrever testes das regras de negócio**

Criar `tests/test_business_rules.py`:

```python
"""
Testes das regras de negócio — sem chamadas à API.
Todas as funções são puras (só lógica Python).
"""
import pytest
from src.business_rules import (
    calculate_score,
    check_minimum_volume,
    is_state_served,
    is_product_available,
    check_auto_disqualification,
)


class TestScoring:
    def test_score_zero_for_no_volume(self):
        assert calculate_score(volume_estimate=None, urgency=None) == 0

    def test_score_increases_with_tonnage(self):
        score_small = calculate_score(volume_estimate="1 tonelada", urgency=None)
        score_large = calculate_score(volume_estimate="50 toneladas", urgency=None)
        assert score_large > score_small

    def test_urgency_bonus(self):
        score_no_urgency = calculate_score(volume_estimate="5 toneladas", urgency=None)
        score_urgent = calculate_score(volume_estimate="5 toneladas", urgency="urgente")
        assert score_urgent > score_no_urgency

    def test_score_max_100(self):
        score = calculate_score(volume_estimate="1000 toneladas", urgency="urgente")
        assert score <= 100


class TestVolumeMinimum:
    def test_below_minimum_returns_false(self):
        assert check_minimum_volume("500kg", state="CE") is False

    def test_above_minimum_returns_true(self):
        assert check_minimum_volume("2 toneladas", state="CE") is True

    def test_none_volume_returns_false(self):
        assert check_minimum_volume(None, state="CE") is False


class TestStateServed:
    def test_ceara_is_served(self):
        assert is_state_served("CE") is True

    def test_sao_paulo_is_not_served(self):
        assert is_state_served("SP") is False

    def test_case_insensitive(self):
        assert is_state_served("ce") is True


class TestProductAvailable:
    def test_vergalhao_is_available(self):
        assert is_product_available("Vergalhão") is True

    def test_unknown_product_returns_false(self):
        assert is_product_available("produto_inexistente_xyz") is False


class TestAutoDisqualification:
    def test_disqualify_out_of_state(self):
        result = check_auto_disqualification(
            state="SP", volume_estimate="5 toneladas", product="Vergalhão"
        )
        assert result["disqualified"] is True
        assert "estado" in result["reason"].lower()

    def test_disqualify_low_volume(self):
        result = check_auto_disqualification(
            state="CE", volume_estimate="100kg", product="Vergalhão"
        )
        assert result["disqualified"] is True
        assert "volume" in result["reason"].lower()

    def test_qualify_valid_lead(self):
        result = check_auto_disqualification(
            state="CE", volume_estimate="5 toneladas", product="Vergalhão"
        )
        assert result["disqualified"] is False
```

**Step 2: Rodar e verificar que falha**
```bash
pytest tests/test_business_rules.py -v
```
Esperado: `ModuleNotFoundError: No module named 'src.business_rules'`

**Step 3: Implementar business_rules.py**

Criar `src/business_rules.py`:

```python
"""
Regras de negócio da Aço Cearense.

Todas as funções são puras (sem side effects) para facilitar testes.
Regras baseadas nos documentos fornecidos pelo cliente.
"""
import re
from typing import Optional

# Estados atendidos pela distribuidora
STATES_SERVED = {"CE", "PI", "MA", "RN", "PB", "PE", "AL", "SE", "BA"}

# Volume mínimo por pedido (em kg) — regra: mínimo 1500kg ou 20 unidades
MINIMUM_VOLUME_KG = 1500

# Produtos disponíveis (normalizado em lowercase)
AVAILABLE_PRODUCTS = {
    "vergalhão", "vergalhao", "arame recozido", "tubo industrial",
    "tubo quadrado", "tubo retangular", "tubo redondo",
    "telha trapezoidal galvanizada", "chapa galvanizada",
    "barra chata", "cantoneira", "perfil u",
    "metalon", "ferro",  # aceitos como genérico
}


def _parse_volume_to_kg(volume_str: Optional[str]) -> float:
    """
    Converte string de volume para quilogramas.

    Exemplos:
        "5 toneladas" → 5000.0
        "500 kg" → 500.0
        "2t" → 2000.0
        "20 unidades" → 400.0 (estimativa: 20kg/unidade)
    """
    if not volume_str:
        return 0.0

    text = volume_str.lower().strip()

    # Extrair número
    numbers = re.findall(r"[\d.,]+", text)
    if not numbers:
        return 0.0

    try:
        amount = float(numbers[0].replace(",", "."))
    except ValueError:
        return 0.0

    # Converter para kg
    if "ton" in text or text.endswith("t") or " t " in text:
        return amount * 1000
    elif "unidade" in text or " un" in text or "pç" in text or "peça" in text:
        return amount * 20  # estimativa conservadora
    else:
        return amount  # assume kg


def calculate_score(
    volume_estimate: Optional[str],
    urgency: Optional[str],
) -> int:
    """
    Calcula o score de prioridade do lead (0-100).

    Critérios:
    - Volume: até 70 pontos (base: 1 ponto por 100kg, máximo em 7000kg+)
    - Urgência mencionada: +30 pontos bonus

    Args:
        volume_estimate: Texto com volume (ex: "5 toneladas", "500kg")
        urgency: Texto com urgência do cliente (pode ser None)

    Returns:
        int: Score de 0 a 100
    """
    score = 0

    # Pontuação por volume
    volume_kg = _parse_volume_to_kg(volume_estimate)
    if volume_kg > 0:
        # 1 ponto por 100kg, máximo 70 pontos
        volume_score = min(70, int(volume_kg / 100))
        score += volume_score

    # Bônus por urgência
    if urgency and any(
        word in urgency.lower()
        for word in ["urgente", "imediato", "hoje", "amanhã", "semana"]
    ):
        score += 30

    return min(100, score)


def check_minimum_volume(
    volume_estimate: Optional[str],
    state: Optional[str] = None,
) -> bool:
    """
    Verifica se o volume atende ao mínimo exigido (1500kg ou 20 unidades).

    Args:
        volume_estimate: Texto com volume estimado
        state: UF do cliente (futuro: mínimos por estado)

    Returns:
        bool: True se atende ao mínimo
    """
    volume_kg = _parse_volume_to_kg(volume_estimate)
    return volume_kg >= MINIMUM_VOLUME_KG


def is_state_served(state: Optional[str]) -> bool:
    """
    Verifica se o estado é atendido pela distribuidora.

    Args:
        state: Sigla da UF (ex: "CE", "SP")

    Returns:
        bool: True se atendemos esse estado
    """
    if not state:
        return False
    return state.upper().strip() in STATES_SERVED


def is_product_available(product: Optional[str]) -> bool:
    """
    Verifica se o produto existe no portfólio da empresa.

    Args:
        product: Nome técnico ou popular do produto

    Returns:
        bool: True se o produto está disponível
    """
    if not product:
        return False
    product_lower = product.lower().strip()
    return any(p in product_lower or product_lower in p for p in AVAILABLE_PRODUCTS)


def check_auto_disqualification(
    state: Optional[str],
    volume_estimate: Optional[str],
    product: Optional[str],
) -> dict:
    """
    Aplica todas as regras de desqualificação automática.

    Ordem de verificação:
    1. Estado não atendido
    2. Volume abaixo do mínimo
    3. Produto não disponível

    Args:
        state: UF do cliente
        volume_estimate: Volume desejado
        product: Produto de interesse

    Returns:
        dict: {"disqualified": bool, "reason": str}
    """
    # Regra 1: Estado não atendido
    if state and not is_state_served(state):
        return {
            "disqualified": True,
            "reason": (
                f"Infelizmente não atendemos o estado {state.upper()}. "
                "Operamos no Nordeste (CE, PI, MA, RN, PB, PE, AL, SE, BA)."
            ),
        }

    # Regra 2: Volume abaixo do mínimo
    if volume_estimate and not check_minimum_volume(volume_estimate, state):
        return {
            "disqualified": True,
            "reason": (
                f"O volume informado ({volume_estimate}) está abaixo do mínimo "
                "de 1.500kg por pedido para a sua região."
            ),
        }

    # Regra 3: Produto não disponível
    if product and not is_product_available(product):
        return {
            "disqualified": True,
            "reason": (
                f"O produto '{product}' não está disponível no nosso portfólio. "
                "Trabalhamos com vergalhões, tubos, chapas, telhas e perfis estruturais."
            ),
        }

    return {"disqualified": False, "reason": ""}
```

**Step 4: Rodar testes**
```bash
pytest tests/test_business_rules.py -v
```
Esperado: todos PASS

**Step 5: Commit**
```bash
git add src/business_rules.py tests/test_business_rules.py
git commit -m "feat: add business rules module with scoring, volume check, and auto-disqualification"
```

---

### Task 4: Integrar Regras de Negócio na API

**Por que:** A API precisa aplicar as regras de desqualificação e calcular o score antes de retornar a resposta, sem depender do agente de IA fazer isso.

**Files:**
- Modify: `src/api.py`
- Modify: `tests/test_api.py`

**Step 1: Escrever testes da API com regras de negócio**

Em `tests/test_api.py`, adicionar:

```python
def test_out_of_state_lead_gets_disqualified():
    from fastapi.testclient import TestClient
    from src.api import app
    from src.models import IncomingMessage, LeadData

    client = TestClient(app)
    lead = LeadData(session_id="test-sp", state="SP", volume_estimate="5 toneladas")
    msg = IncomingMessage(session_id="test-sp", message="Quero vergalhão", lead_data=lead)
    response = client.post("/chat", json=msg.model_dump())
    assert response.status_code == 200
    data = response.json()
    assert data["lead_data"]["disqualified_reason"] is not None

def test_score_calculated_from_volume():
    from fastapi.testclient import TestClient
    from src.api import app
    from src.models import IncomingMessage, LeadData

    client = TestClient(app)
    lead = LeadData(session_id="test-score", state="CE", volume_estimate="10 toneladas")
    msg = IncomingMessage(session_id="test-score", message="Preciso de vergalhão", lead_data=lead)
    response = client.post("/chat", json=msg.model_dump())
    assert response.status_code == 200
    data = response.json()
    assert data["lead_data"]["score"] > 0
```

**Step 2: Rodar e verificar que falha**
```bash
pytest tests/test_api.py::test_out_of_state_lead_gets_disqualified -v
```

**Step 3: Integrar business_rules na API**

Em `src/api.py`, modificar o endpoint `/chat`:

```python
from fastapi import FastAPI, HTTPException
from src.models import IncomingMessage, AgentResponse, LeadClassification, LeadData
from src.orchestrator import create_steel_sales_team
from src.business_rules import check_auto_disqualification, calculate_score

app = FastAPI(
    title="POC Agno - Agentes de Vendas de Aço",
    description="API de automação do fluxo de atendimento para distribuidora de aço",
    version="0.2.0",
)

_team = None


def get_team():
    global _team
    if _team is None:
        _team = create_steel_sales_team()
    return _team


def extract_classification(response_text: str) -> LeadClassification:
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
        lead_data = message.lead_data or LeadData(session_id=message.session_id)

        # Calcular score antes de chamar o agente
        lead_data.score = calculate_score(
            volume_estimate=lead_data.volume_estimate,
            urgency=lead_data.urgency,
        )

        # Verificar desqualificação automática (sem chamar IA)
        disq = check_auto_disqualification(
            state=lead_data.state,
            volume_estimate=lead_data.volume_estimate,
            product=lead_data.technical_product or lead_data.product_interest,
        )

        if disq["disqualified"]:
            lead_data.disqualified_reason = disq["reason"]
            lead_data.classification = LeadClassification.FRIO
            return AgentResponse(
                session_id=message.session_id,
                message=disq["reason"],
                classification=LeadClassification.FRIO,
                lead_data=lead_data,
                next_action="disqualified",
            )

        # Chamar agentes apenas se não desqualificado
        team = get_team()
        context = message.message
        if message.lead_data:
            context = f"[DADOS DO LEAD: {lead_data.model_dump_json()}]\n\nMensagem do cliente: {message.message}"

        response = team.run(context)
        content = response.content if hasattr(response, "content") else str(response)
        classification = extract_classification(content)

        lead_data.classification = classification

        return AgentResponse(
            session_id=message.session_id,
            message=content,
            classification=classification,
            lead_data=lead_data,
            next_action=(
                "collect_data" if classification == LeadClassification.FRIO else
                "generate_quote" if classification == LeadClassification.MORNO else
                "transfer_to_closer"
            ),
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
        },
    }
```

**Step 4: Rodar testes**
```bash
pytest tests/test_api.py -v
```
Esperado: todos PASS

**Step 5: Commit**
```bash
git add src/api.py tests/test_api.py
git commit -m "feat: integrate business rules (scoring + auto-disqualification) into API"
```

---

### Task 5: Criar Agente de Transbordo Humanizado

**Por que:** O cliente quer que a IA transfira para humano quando: 3 respostas incoerentes, cliente pede humano explicitamente, ou caso complexo.

**Files:**
- Create: `src/agents/human_handoff_agent.py`
- Create: `tests/test_human_handoff_agent.py`
- Modify: `src/orchestrator.py`

**Step 1: Escrever testes do agente de transbordo**

Criar `tests/test_human_handoff_agent.py`:

```python
import pytest
from src.agents.human_handoff_agent import (
    create_human_handoff_agent,
    detect_handoff_trigger,
    HANDOFF_TRIGGERS,
)


class TestHandoffDetection:
    def test_detect_explicit_human_request(self):
        result = detect_handoff_trigger("quero falar com um humano")
        assert result["should_handoff"] is True
        assert result["reason"] == "explicit_request"

    def test_detect_atendente_request(self):
        result = detect_handoff_trigger("pode me passar para um atendente?")
        assert result["should_handoff"] is True

    def test_detect_gerente_request(self):
        result = detect_handoff_trigger("preciso falar com o gerente")
        assert result["should_handoff"] is True

    def test_normal_message_no_handoff(self):
        result = detect_handoff_trigger("quero 5 toneladas de vergalhão")
        assert result["should_handoff"] is False

    def test_agent_created(self):
        agent = create_human_handoff_agent()
        assert agent is not None
        assert agent.name == "Agente de Transbordo"
```

**Step 2: Rodar e verificar que falha**
```bash
pytest tests/test_human_handoff_agent.py -v
```
Esperado: `ModuleNotFoundError`

**Step 3: Implementar human_handoff_agent.py**

Criar `src/agents/human_handoff_agent.py`:

```python
"""
Agente de Transbordo Humanizado.

Detecta quando o atendimento deve ser transferido para um humano e
gera a mensagem de handoff adequada.

Triggers para transbordo:
1. Cliente pede explicitamente por humano/atendente/gerente
2. Orquestrador detecta 3+ respostas incoerentes seguidas
3. Caso marcado como "complexo" pelo orquestrador
"""
from agno.agent import Agent
from src.config import get_model

# Palavras/frases que indicam pedido explícito de atendimento humano
HANDOFF_TRIGGERS = [
    "falar com humano",
    "falar com pessoa",
    "falar com atendente",
    "falar com vendedor",
    "falar com gerente",
    "atendimento humano",
    "quero humano",
    "preciso de humano",
    "me passa para",
    "transferir para",
    "pessoa real",
    "não quero robô",
    "não quero bot",
    "fala com alguém",
]

HUMAN_HANDOFF_INSTRUCTIONS = """
Você é o Agente de Transbordo de uma distribuidora de produtos de aço.

Sua única função é informar ao cliente, de forma empática e profissional,
que ele será transferido para um atendente humano.

## Mensagem padrão:

Gere sempre uma mensagem que:
1. Agradeça pela paciência
2. Confirme que vai transferir para um humano especializado
3. Informe prazo de retorno (até 30 minutos em horário comercial)
4. Deixe o cliente confortável para aguardar

## Exemplos de motivo para transbordo:
- Cliente pediu atendimento humano
- Caso de alta complexidade
- Sistema detectou dificuldade de comunicação

Seja cordial, breve e tranquilizador.
"""


def detect_handoff_trigger(message: str) -> dict:
    """
    Detecta se a mensagem do cliente contém pedido de atendimento humano.

    Args:
        message: Texto da mensagem do cliente

    Returns:
        dict: {"should_handoff": bool, "reason": str}
    """
    message_lower = message.lower()

    for trigger in HANDOFF_TRIGGERS:
        if trigger in message_lower:
            return {
                "should_handoff": True,
                "reason": "explicit_request",
                "trigger_found": trigger,
            }

    return {"should_handoff": False, "reason": ""}


def create_human_handoff_agent() -> Agent:
    """
    Cria o agente de transbordo humanizado.

    Usado pelo orquestrador quando detecta que o caso deve ir para humano.
    """
    return Agent(
        name="Agente de Transbordo",
        model=get_model(),
        instructions=HUMAN_HANDOFF_INSTRUCTIONS,
        markdown=True,
    )
```

**Step 4: Atualizar orchestrator.py para usar o handoff**

Em `src/orchestrator.py`, modificar para incluir o 4º agente e a lógica de handoff:

```python
from agno.team import Team
from agno.db.sqlite import SqliteDb
from src.config import get_model
from src.agents.qualifier_agent import create_qualifier_agent
from src.agents.product_specialist_agent import create_product_specialist_agent
from src.agents.quote_generator_agent import create_quote_generator_agent
from src.agents.human_handoff_agent import create_human_handoff_agent

ORCHESTRATOR_INSTRUCTIONS = """
Você é o Orquestrador do sistema de atendimento de uma distribuidora de produtos de aço.

Coordene os agentes especializados para qualificar leads e gerar orçamentos:
1. **Qualificador de Leads** - Coleta dados e classifica o lead (FRIO/MORNO/QUENTE)
2. **Especialista de Produtos** - Traduz termos populares para nomenclatura técnica
3. **Gerador de Orçamentos** - Cria resumo estruturado quando lead é MORNO
4. **Agente de Transbordo** - Transfere para humano quando necessário

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
Tentativas incoerentes: [número de 0 a 3]
---FIM DO CONTEXTO---

Última mensagem do cliente: [mensagem]
---

Nunca delegue sem esse bloco. O agente membro NÃO tem memória própria — você é o único guardião do estado da conversa.

## Fluxo de decisão:
- Cliente pede humano / atendente / gerente → Agente de Transbordo (IMEDIATO)
- 3 ou mais tentativas incoerentes seguidas → Agente de Transbordo
- Mensagem inicial ou dados incompletos → Qualificador de Leads
- Cliente menciona produto específico → Especialista de Produtos (inclua contexto acumulado)
- Todos os dados coletados (MORNO) → Gerador de Orçamentos (inclua contexto acumulado)

## Regras:
- NUNCA peça informações que já foram fornecidas
- NUNCA reinicie a conversa do zero
- Atualize o bloco CONTEXTO ACUMULADO a cada turno com as novas informações recebidas
- Incremente "Tentativas incoerentes" quando o cliente der respostas sem sentido
"""


def create_steel_sales_team() -> Team:
    qualifier = create_qualifier_agent()
    product_specialist = create_product_specialist_agent()
    quote_generator = create_quote_generator_agent()
    human_handoff = create_human_handoff_agent()

    team = Team(
        name="Time de Vendas de Aço",
        mode="coordinate",
        model=get_model(),
        members=[qualifier, product_specialist, quote_generator, human_handoff],
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

**Step 5: Atualizar api.py para detectar handoff antes de chamar agentes**

Em `src/api.py`, antes de chamar `team.run()`, adicionar detecção de handoff:

```python
from src.agents.human_handoff_agent import detect_handoff_trigger

# Verificar handoff explícito (antes de chamar IA para economizar tokens)
handoff = detect_handoff_trigger(message.message)
if handoff["should_handoff"]:
    return AgentResponse(
        session_id=message.session_id,
        message=(
            "Claro! Vou transferir você para um de nossos atendentes especializados. "
            "Em até 30 minutos (horário comercial) alguém entrará em contato. "
            "Obrigado pela preferência! 😊"
        ),
        classification=LeadClassification.MORNO,  # leads que pedem humano têm potencial
        lead_data=lead_data,
        next_action="human_handoff",
    )
```

**Step 6: Rodar todos os testes**
```bash
pytest tests/ -v -k "not test_classify_incomplete_lead_as_frio"
```
Esperado: todos PASS

**Step 7: Commit**
```bash
git add src/agents/human_handoff_agent.py tests/test_human_handoff_agent.py src/orchestrator.py src/api.py
git commit -m "feat: add humanized handoff agent with explicit trigger detection"
```

---

### Task 6: Criar Sistema de Follow-up Cadenciado

**Por que:** Após o Closer enviar um orçamento, a IA deve fazer cobranças automáticas em 2h, 10h, 20h e 48h se o cliente não responder.

**Files:**
- Create: `src/followup_scheduler.py`
- Create: `tests/test_followup_scheduler.py`

**Step 1: Instalar APScheduler**

Adicionar em `pyproject.toml` na lista de dependencies:
```
"apscheduler>=3.10.0",
```

Instalar:
```bash
pip install apscheduler>=3.10.0
```

**Step 2: Escrever testes do scheduler**

Criar `tests/test_followup_scheduler.py`:

```python
"""
Testes do sistema de follow-up cadenciado.
Testa a lógica de estado sem inicializar o scheduler real.
"""
import pytest
from datetime import datetime, timedelta
from src.followup_scheduler import (
    FollowUpState,
    FollowUpManager,
    FOLLOWUP_INTERVALS_HOURS,
)


class TestFollowUpIntervals:
    def test_correct_intervals(self):
        assert FOLLOWUP_INTERVALS_HOURS == [2, 10, 20, 48]


class TestFollowUpState:
    def test_initial_state(self):
        state = FollowUpState(session_id="test-001", lead_name="João")
        assert state.attempt == 0
        assert state.completed is False
        assert state.session_id == "test-001"

    def test_max_attempts_is_four(self):
        state = FollowUpState(session_id="test-001", lead_name="João")
        assert state.max_attempts == 4


class TestFollowUpManager:
    def test_register_lead_for_followup(self):
        manager = FollowUpManager(dry_run=True)
        manager.register(session_id="sess-001", lead_name="Carlos", contact="11999998888")
        assert manager.has_pending("sess-001") is True

    def test_cancel_followup(self):
        manager = FollowUpManager(dry_run=True)
        manager.register(session_id="sess-001", lead_name="Carlos", contact="11999998888")
        manager.cancel("sess-001")
        assert manager.has_pending("sess-001") is False

    def test_get_followup_message_first(self):
        manager = FollowUpManager(dry_run=True)
        msg = manager._build_message(lead_name="Carlos", attempt=1)
        assert "Carlos" in msg
        assert len(msg) > 20

    def test_get_followup_message_last(self):
        manager = FollowUpManager(dry_run=True)
        msg = manager._build_message(lead_name="Carlos", attempt=4)
        assert "Carlos" in msg
```

**Step 3: Rodar e verificar que falha**
```bash
pytest tests/test_followup_scheduler.py -v
```

**Step 4: Implementar followup_scheduler.py**

Criar `src/followup_scheduler.py`:

```python
"""
Sistema de Follow-up Cadenciado Pós-Orçamento.

Quando um Closer envia orçamento e o cliente não responde, este módulo
agenda mensagens automáticas de acompanhamento nos intervalos:
  - 2 horas após orçamento
  - 10 horas após orçamento
  - 20 horas após orçamento
  - 48 horas após orçamento → encerra o ticket por inatividade

Uso:
    manager = FollowUpManager()
    manager.register(session_id="sess-001", lead_name="Carlos", contact="11999998888")

    # Quando cliente responder:
    manager.cancel("sess-001")
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# Intervalos em horas: 2h, 10h, 20h, 48h
FOLLOWUP_INTERVALS_HOURS = [2, 10, 20, 48]

# Mensagens para cada tentativa (1-indexed)
FOLLOWUP_MESSAGES = {
    1: (
        "Olá, {name}! 👋 Passando para saber se você teve a oportunidade de "
        "analisar o orçamento que enviamos. Ficamos à disposição para tirar dúvidas!"
    ),
    2: (
        "Oi, {name}! Tudo bem? Gostaríamos de saber se o nosso orçamento atendeu "
        "às suas expectativas. Posso ajudar com alguma informação adicional? 😊"
    ),
    3: (
        "{name}, como vai? Sabemos que você está ocupado! Nosso orçamento ainda "
        "está disponível. Se precisar de qualquer ajuste nos prazos ou quantidades, "
        "é só falar!"
    ),
    4: (
        "Olá, {name}! Esta é nossa última mensagem de acompanhamento. "
        "Caso queira retomar o contato futuramente, é só nos chamar. "
        "Agradecemos o interesse na Aço Cearense! 🙏"
    ),
}


@dataclass
class FollowUpState:
    """Estado do follow-up de um lead específico."""
    session_id: str
    lead_name: str
    contact: str  # WhatsApp ou email
    attempt: int = 0
    max_attempts: int = 4
    completed: bool = False
    registered_at: datetime = field(default_factory=datetime.now)
    last_attempt_at: Optional[datetime] = None


class FollowUpManager:
    """
    Gerenciador de follow-ups.

    Em produção, usa APScheduler para agendar as mensagens.
    Em modo dry_run=True (testes), apenas registra o estado sem agendar.

    Args:
        dry_run: Se True, não inicializa o scheduler (para testes).
    """

    def __init__(self, dry_run: bool = False):
        self._states: dict[str, FollowUpState] = {}
        self._dry_run = dry_run

        if not dry_run:
            self._init_scheduler()

    def _init_scheduler(self):
        """Inicializa APScheduler para produção."""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            self._scheduler = BackgroundScheduler()
            self._scheduler.start()
        except ImportError:
            raise ImportError(
                "APScheduler não instalado. Execute: pip install apscheduler>=3.10.0"
            )

    def register(self, session_id: str, lead_name: str, contact: str):
        """
        Registra um lead para receber follow-ups.

        Agenda mensagens nos intervalos: 2h, 10h, 20h e 48h.

        Args:
            session_id: ID único da conversa
            lead_name: Nome do lead para personalizar mensagens
            contact: WhatsApp ou email do lead
        """
        state = FollowUpState(
            session_id=session_id,
            lead_name=lead_name,
            contact=contact,
        )
        self._states[session_id] = state

        if not self._dry_run:
            from datetime import timedelta
            from apscheduler.triggers.date import DateTrigger

            for i, hours in enumerate(FOLLOWUP_INTERVALS_HOURS, start=1):
                run_time = datetime.now() + timedelta(hours=hours)
                self._scheduler.add_job(
                    func=self._execute_followup,
                    trigger=DateTrigger(run_date=run_time),
                    args=[session_id, i],
                    id=f"{session_id}_attempt_{i}",
                    replace_existing=True,
                )

    def cancel(self, session_id: str):
        """
        Cancela todos os follow-ups pendentes de um lead.
        Chamar quando o cliente responder.

        Args:
            session_id: ID da conversa a cancelar
        """
        if session_id in self._states:
            self._states[session_id].completed = True

        if not self._dry_run and hasattr(self, "_scheduler"):
            for i in range(1, 5):
                job_id = f"{session_id}_attempt_{i}"
                try:
                    self._scheduler.remove_job(job_id)
                except Exception:
                    pass  # job já executado ou não existe

    def has_pending(self, session_id: str) -> bool:
        """
        Verifica se há follow-up pendente para a sessão.

        Returns:
            bool: True se há follow-up registrado e não concluído
        """
        state = self._states.get(session_id)
        return state is not None and not state.completed

    def _build_message(self, lead_name: str, attempt: int) -> str:
        """
        Constrói a mensagem de follow-up para a tentativa N.

        Args:
            lead_name: Nome do lead
            attempt: Número da tentativa (1-4)

        Returns:
            str: Mensagem formatada
        """
        template = FOLLOWUP_MESSAGES.get(attempt, FOLLOWUP_MESSAGES[4])
        return template.format(name=lead_name)

    def _execute_followup(self, session_id: str, attempt: int):
        """
        Executa o follow-up (chamado pelo scheduler).

        Em produção, aqui enviaria a mensagem via API do Blip/WhatsApp.
        Por enquanto, loga a mensagem (stub para integração futura).
        """
        state = self._states.get(session_id)
        if not state or state.completed:
            return

        message = self._build_message(state.lead_name, attempt)
        state.attempt = attempt
        state.last_attempt_at = datetime.now()

        # Stub: em produção, chamar API do Blip/WhatsApp aqui
        print(f"[FOLLOW-UP] session={session_id} attempt={attempt}/{state.max_attempts}")
        print(f"[FOLLOW-UP] contact={state.contact}")
        print(f"[FOLLOW-UP] message={message}")

        if attempt >= state.max_attempts:
            state.completed = True
            print(f"[FOLLOW-UP] Ticket {session_id} encerrado por inatividade.")
```

**Step 5: Adicionar endpoint de follow-up na API**

Em `src/api.py`, adicionar endpoint para registrar follow-up:

```python
from src.followup_scheduler import FollowUpManager

_followup_manager = FollowUpManager(dry_run=False)


@app.post("/followup/register")
async def register_followup(session_id: str, lead_name: str, contact: str):
    """
    Registra um lead para receber follow-ups automáticos pós-orçamento.
    Chamar quando o Closer enviar o orçamento.
    """
    _followup_manager.register(session_id=session_id, lead_name=lead_name, contact=contact)
    return {"status": "registered", "session_id": session_id}


@app.post("/followup/cancel")
async def cancel_followup(session_id: str):
    """
    Cancela os follow-ups de um lead (quando ele responde).
    """
    _followup_manager.cancel(session_id=session_id)
    return {"status": "cancelled", "session_id": session_id}
```

**Step 6: Rodar testes**
```bash
pytest tests/test_followup_scheduler.py -v
```
Esperado: todos PASS

**Step 7: Commit**
```bash
git add src/followup_scheduler.py tests/test_followup_scheduler.py src/api.py pyproject.toml
git commit -m "feat: add cadenced follow-up scheduler (2h, 10h, 20h, 48h) with cancel support"
```

---

### Task 7: Criar Stub de Integração CRM (Salesforce)

**Por que:** O cliente quer atualizar o CRM (Salesforce) quando o status do lead muda. Esta task cria um módulo stub que pode ser conectado à API real do Salesforce depois.

**Files:**
- Create: `src/crm_integration.py`
- Create: `tests/test_crm_integration.py`

**Step 1: Escrever testes do stub CRM**

Criar `tests/test_crm_integration.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from src.crm_integration import CRMClient, LeadStatus


class TestCRMClient:
    def test_stub_mode_does_not_raise(self):
        client = CRMClient(stub_mode=True)
        # Não deve lançar exceção
        client.update_lead_status(lead_id="LEAD-001", status=LeadStatus.MORNO, score=75)

    def test_stub_mode_returns_success(self):
        client = CRMClient(stub_mode=True)
        result = client.update_lead_status(
            lead_id="LEAD-001", status=LeadStatus.QUENTE, score=90
        )
        assert result["success"] is True

    def test_stub_mode_create_lead(self):
        client = CRMClient(stub_mode=True)
        result = client.create_lead(
            name="Carlos", email="c@test.com", phone="11999998888", cnpj="12345678000100"
        )
        assert result["success"] is True
        assert "id" in result

    def test_lead_status_values(self):
        assert LeadStatus.FRIO == "FRIO"
        assert LeadStatus.MORNO == "MORNO"
        assert LeadStatus.QUENTE == "QUENTE"
        assert LeadStatus.DESQUALIFICADO == "DESQUALIFICADO"
```

**Step 2: Rodar e verificar que falha**
```bash
pytest tests/test_crm_integration.py -v
```

**Step 3: Implementar crm_integration.py**

Criar `src/crm_integration.py`:

```python
"""
Integração CRM — Stub para Salesforce.

Este módulo é um STUB (simulação) da integração com o Salesforce.
Em produção, substitua os métodos `_stub_*` por chamadas reais à API
do Salesforce usando a biblioteca `simple-salesforce`.

Como conectar ao Salesforce real:
    pip install simple-salesforce

    from simple_salesforce import Salesforce
    sf = Salesforce(
        username=os.getenv("SF_USERNAME"),
        password=os.getenv("SF_PASSWORD"),
        security_token=os.getenv("SF_SECURITY_TOKEN"),
    )

Campos do Salesforce que serão atualizados:
    - Lead.Status → FRIO, MORNO, QUENTE, DESQUALIFICADO
    - Lead.Lead_Score__c → score numérico (0-100)
    - Lead.Disqualification_Reason__c → motivo da desqualificação
"""
import os
import uuid
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class LeadStatus(str, Enum):
    FRIO = "FRIO"
    MORNO = "MORNO"
    QUENTE = "QUENTE"
    DESQUALIFICADO = "DESQUALIFICADO"


class CRMClient:
    """
    Cliente de integração com CRM.

    Args:
        stub_mode: Se True, simula as chamadas sem fazer requests reais.
                   Use True em desenvolvimento e testes.
    """

    def __init__(self, stub_mode: bool = True):
        self._stub_mode = stub_mode

        if not stub_mode:
            self._init_salesforce()

    def _init_salesforce(self):
        """Inicializa conexão real com Salesforce."""
        # TODO: Implementar quando integração for aprovada
        # from simple_salesforce import Salesforce
        # self._sf = Salesforce(
        #     username=os.getenv("SF_USERNAME"),
        #     password=os.getenv("SF_PASSWORD"),
        #     security_token=os.getenv("SF_SECURITY_TOKEN"),
        # )
        raise NotImplementedError(
            "Integração Salesforce não implementada. Use stub_mode=True para desenvolvimento."
        )

    def update_lead_status(
        self,
        lead_id: str,
        status: LeadStatus,
        score: int = 0,
        disqualification_reason: Optional[str] = None,
    ) -> dict:
        """
        Atualiza o status e score do lead no CRM.

        Args:
            lead_id: ID do lead no Salesforce
            status: Novo status (FRIO, MORNO, QUENTE, DESQUALIFICADO)
            score: Score numérico de 0-100
            disqualification_reason: Motivo da desqualificação (se aplicável)

        Returns:
            dict: {"success": bool, "lead_id": str}
        """
        if self._stub_mode:
            return self._stub_update_lead_status(lead_id, status, score, disqualification_reason)

        # Produção: implementar chamada real
        # self._sf.Lead.update(lead_id, {
        #     "Status": status.value,
        #     "Lead_Score__c": score,
        #     "Disqualification_Reason__c": disqualification_reason,
        # })
        raise NotImplementedError("Modo produção não implementado")

    def create_lead(
        self,
        name: str,
        email: str,
        phone: str,
        cnpj: Optional[str] = None,
        company: Optional[str] = None,
    ) -> dict:
        """
        Cria um novo lead no CRM.

        Args:
            name: Nome completo do lead
            email: E-mail de contato
            phone: WhatsApp com DDD
            cnpj: CNPJ da empresa (opcional)
            company: Nome da empresa (opcional)

        Returns:
            dict: {"success": bool, "id": str}
        """
        if self._stub_mode:
            return self._stub_create_lead(name, email, phone, cnpj, company)

        raise NotImplementedError("Modo produção não implementado")

    def _stub_update_lead_status(
        self, lead_id: str, status: LeadStatus, score: int, reason: Optional[str]
    ) -> dict:
        """Simula atualização de status no CRM."""
        logger.info(
            f"[CRM STUB] update_lead: id={lead_id} status={status.value} score={score}"
        )
        if reason:
            logger.info(f"[CRM STUB] disqualification_reason={reason}")
        return {"success": True, "lead_id": lead_id}

    def _stub_create_lead(
        self, name: str, email: str, phone: str, cnpj: Optional[str], company: Optional[str]
    ) -> dict:
        """Simula criação de lead no CRM."""
        fake_id = f"STUB-{str(uuid.uuid4())[:8].upper()}"
        logger.info(f"[CRM STUB] create_lead: name={name} email={email} id={fake_id}")
        return {"success": True, "id": fake_id}
```

**Step 4: Rodar testes**
```bash
pytest tests/test_crm_integration.py -v
```
Esperado: todos PASS

**Step 5: Commit**
```bash
git add src/crm_integration.py tests/test_crm_integration.py
git commit -m "feat: add Salesforce CRM stub integration with lead status update and creation"
```

---

### Task 8: Rodar Suite Completa e Verificar

**Step 1: Rodar todos os testes sem API key**
```bash
pytest tests/ -v -k "not test_classify_incomplete_lead_as_frio"
```
Esperado: todos PASS

**Step 2: Verificar cobertura**
```bash
pip install pytest-cov
pytest tests/ --cov=src --cov-report=term-missing -k "not test_classify_incomplete_lead_as_frio"
```

**Step 3: Commit final**
```bash
git add .
git commit -m "chore: verify all tests pass after complete gap implementation"
```

---

## Resumo Final de Gaps

| Gap | Implementado em | Arquivo |
|-----|----------------|---------|
| Scoring numérico | Task 2+3 | `src/models.py` + `src/business_rules.py` |
| Desqualificação automática | Task 3+4 | `src/business_rules.py` + `src/api.py` |
| Transbordo humanizado | Task 5 | `src/agents/human_handoff_agent.py` |
| Follow-up cadenciado | Task 6 | `src/followup_scheduler.py` |
| CRM Salesforce (stub) | Task 7 | `src/crm_integration.py` |
| Documentação técnica | Task 1 | `docs/ARCHITECTURE.md` |

### O que ainda precisa de infra externa para produção:
- **WhatsApp/Blip:** Criar webhook POST `/webhook/blip` que receba mensagens e chame `POST /chat`
- **Salesforce real:** Configurar credenciais SF e mudar `stub_mode=False` no `CRMClient`
- **Servidor persistente:** Deploy com Docker + Postgres (trocar SQLite) para escalar

---
*Plano criado em 2026-02-21*
