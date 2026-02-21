# Arquitetura Técnica — POC Agno Steel Agents

> Sistema multi-agente para automatizar o atendimento e qualificação de leads de uma distribuidora de produtos de aço (Aço Cearense), usando o framework Agno 2.5.3 com LLMs da Google (Gemini) ou Anthropic (Claude).

---

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Diagrama da Arquitetura](#2-diagrama-da-arquitetura)
3. [Referência de Arquivos](#3-referência-de-arquivos)
   - [src/config.py](#31-srcconfigpy)
   - [src/models.py](#32-srcmodelspy)
   - [src/knowledge_builder.py](#33-srcknowledge_builderpy)
   - [src/orchestrator.py](#34-srcorchestratorpy)
   - [src/agents/qualifier_agent.py](#35-srcagentsqualifier_agentpy)
   - [src/agents/product_specialist_agent.py](#36-srcagentsproduct_specialist_agentpy)
   - [src/agents/quote_generator_agent.py](#37-srcagentsquote_generator_agentpy)
   - [src/api.py](#38-srcapipy)
   - [src/agent_os_server.py](#39-srcagent_os_serverpy)
   - [scripts/build_knowledge.py](#310-scriptsbuild_knowledgepy)
   - [scripts/demo_chat.py](#311-scriptsdemo_chatpy)
4. [Dados e Persistência](#4-dados-e-persistência)
5. [Variáveis de Ambiente](#5-variáveis-de-ambiente)
6. [Fluxo Completo de uma Conversa](#6-fluxo-completo-de-uma-conversa)
7. [Classificação de Leads](#7-classificação-de-leads)
8. [Como Rodar](#8-como-rodar)
9. [Testes](#9-testes)
10. [Dependências](#10-dependências)
11. [Como Escalar e Manter](#11-como-escalar-e-manter)

---

## 1. Visão Geral

O sistema simula um atendente virtual de WhatsApp que recebe mensagens de potenciais compradores de produtos de aço. O objetivo é **qualificar o lead** (coletar os dados obrigatórios), **traduzir a linguagem popular** para nomenclatura técnica (ex: "ferro de laje" → "Vergalhão SI 50") e, quando o lead está pronto, **gerar um resumo estruturado** para o time de vendas (Closer) dar continuidade ao atendimento humano.

O sistema utiliza três agentes especializados coordenados por um **Agno Team** no modo `coordinate`, onde o orquestrador decide qual agente acionar em cada turno da conversa.

---

## 2. Diagrama da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CANAL DE ENTRADA                                │
│                                                                         │
│   WhatsApp / Blip / Agent UI (porta 7777) / CLI (demo_chat.py)         │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │ HTTP POST /chat
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    FastAPI  (src/api.py)  :8000                         │
│                                                                         │
│   POST /chat  ──►  IncomingMessage (session_id, message, lead_data?)   │
│   GET  /health ──► {"status": "ok"}                                    │
│   GET  /       ──► lista de endpoints                                  │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │ team.run(context)
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│            AGNO TEAM — Orquestrador  (src/orchestrator.py)              │
│                                                                         │
│   mode="coordinate"  │  LLM: Gemini / Claude (via config.py)           │
│   SQLite session storage ──► data/agent_sessions.db                    │
│   Mantém histórico dos últimos 5 turnos na memória dos membros         │
│                                                                         │
│   Lógica de delegação (via CONTEXTO ACUMULADO):                        │
│   ┌──────────────────────────────────────────────────────────────┐     │
│   │  dados incompletos  ──►  Qualificador de Leads               │     │
│   │  produto mencionado ──►  Especialista de Produtos            │     │
│   │  todos dados OK     ──►  Gerador de Orçamentos               │     │
│   └──────────────────────────────────────────────────────────────┘     │
└──────────┬──────────────────────┬───────────────────────┬──────────────┘
           │                      │                        │
           ▼                      ▼                        ▼
┌─────────────────┐  ┌─────────────────────┐  ┌──────────────────────┐
│  Qualificador   │  │   Especialista de   │  │  Gerador de          │
│  de Leads       │  │   Produtos          │  │  Orçamentos          │
│                 │  │                     │  │                      │
│  Coleta campos  │  │  Linguagem popular  │  │  Gera resumo         │
│  obrigatórios   │  │  → nomenclatura     │  │  estruturado para    │
│  Classifica:    │  │    técnica          │  │  o Closer            │
│  FRIO/MORNO/    │  │                     │  │                      │
│  QUENTE         │  │  Usa knowledge base │  │  Não usa knowledge   │
│                 │  │  (LanceDB + RAG)    │  │  base                │
│  Usa knowledge  │  └─────────────────────┘  └──────────────────────┘
│  base           │
└────────┬────────┘
         │ search_knowledge
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  KNOWLEDGE BASE  (src/knowledge_builder.py)             │
│                                                                         │
│   FastEmbedEmbedder (paraphrase-multilingual-MiniLM-L12-v2, local)     │
│   LanceDB hybrid search (vector + keyword)                             │
│   Tabela: steel_sales_knowledge                                        │
│                                                                         │
│   PDFs indexados:                                                       │
│   ├── knowledge/dicionario_produtos.pdf                                 │
│   ├── knowledge/processo_classificacao.pdf                              │
│   └── knowledge/estrategia_captacao.pdf                                 │
│                                                                         │
│   Armazenado em: data/lancedb/                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Referência de Arquivos

### 3.1 `src/config.py`

**Responsabilidade:** Carrega variáveis de ambiente e fornece a factory de modelo LLM configurável.

#### Variáveis de módulo

| Variável | Tipo | Origem | Descrição |
|---|---|---|---|
| `GOOGLE_API_KEY` | `str \| None` | `.env` | Chave de API Google Gemini |
| `ANTHROPIC_API_KEY` | `str \| None` | `.env` | Chave de API Anthropic Claude |
| `MODEL_ID` | `str` | `.env` (padrão: `gemini-2.5-flash-preview-04-17`) | ID do modelo LLM a usar |
| `KNOWLEDGE_BASE_DIR` | `str` | hardcoded | Diretório dos PDFs fonte (`"knowledge"`) |
| `VECTOR_DB_PATH` | `str` | hardcoded | Caminho do vector DB LanceDB (`"data/lancedb"`) |

#### Funções

**`get_model() -> Gemini | Claude`**

Retorna a instância correta do modelo LLM baseando-se no prefixo do `MODEL_ID`:
- Se começa com `"gemini"` → retorna `agno.models.google.Gemini(id=MODEL_ID)`
- Caso contrário → retorna `agno.models.anthropic.Claude(id=MODEL_ID)`

**Como manter:** Para adicionar suporte a outro provedor (ex: OpenAI), adicione uma nova condição no `if/elif` da função `get_model()` e inclua o pacote Python correspondente no `pyproject.toml`.

---

### 3.2 `src/models.py`

**Responsabilidade:** Define todos os modelos de dados Pydantic usados na API e no sistema de classificação de leads.

#### Enums

**`LeadClassification(str, Enum)`**

| Valor | Significado |
|---|---|
| `FRIO` | Lead com dados incompletos — ainda em coleta |
| `MORNO` | Todos os campos obrigatórios coletados — pronto para orçamento |
| `QUENTE` | Orçamento gerado e repassado ao Closer |

**`ProductCategory(str, Enum)`**

| Valor | Categoria |
|---|---|
| `CONSTRUCAO_CIVIL` | Vergalhões, arame recozido |
| `ESTRUTURAL_SERRALHERIA` | Cantoneiras, barra chata |
| `PLANOS` | Chapas, telhas |
| `TUBOS` | Tubos industriais, tubos quadrados/retangulares |

**`ClientType(str, Enum)`**

Valores: `CONSTRUTORA`, `SERRALHERIA`, `REVENDA`, `OUTRO`

#### Classes Pydantic

**`LeadData(BaseModel)`**

Representa o estado acumulado de um lead ao longo da conversa.

| Campo | Tipo | Obrigatório para MORNO | Descrição |
|---|---|---|---|
| `session_id` | `str` | — | Identificador único da sessão |
| `name` | `str \| None` | Sim | Nome completo do contato |
| `whatsapp` | `str \| None` | Sim | WhatsApp com DDD |
| `email` | `str \| None` | Sim | E-mail de contato |
| `cnpj` | `str \| None` | Sim | CNPJ (14 dígitos, válido) |
| `state` | `str \| None` | Sim | UF (estado) |
| `city` | `str \| None` | Sim | Cidade |
| `client_type` | `ClientType \| None` | Não | Tipo do cliente |
| `product_interest` | `str \| None` | Sim | Produto de interesse (linguagem do cliente) |
| `technical_product` | `str \| None` | Não | Produto em nomenclatura técnica |
| `volume_estimate` | `str \| None` | Sim | Volume estimado (ex: "10 toneladas") |
| `urgency` | `str \| None` | Não | Urgência do pedido |
| `classification` | `LeadClassification` | — | Status atual (padrão: FRIO) |
| `missing_fields` | `list[str]` | — | Campos ainda faltantes |

**`IncomingMessage(BaseModel)`**

Payload recebido pelo endpoint `POST /chat`.

| Campo | Tipo | Descrição |
|---|---|---|
| `session_id` | `str` | ID da sessão (usado para rastrear conversa) |
| `message` | `str` | Texto da mensagem do usuário |
| `lead_data` | `LeadData \| None` | Estado atual do lead (opcional, para contexto externo) |

**`AgentResponse(BaseModel)`**

Payload retornado pelo endpoint `POST /chat`.

| Campo | Tipo | Descrição |
|---|---|---|
| `session_id` | `str` | ID da sessão |
| `message` | `str` | Resposta gerada pelos agentes |
| `classification` | `LeadClassification` | Classificação atual do lead |
| `lead_data` | `LeadData` | Estado atualizado do lead |
| `next_action` | `str` | Ação sugerida para o sistema integrador |

Valores possíveis de `next_action`:
- `"collect_data"` — lead FRIO, continuar coletando dados
- `"generate_quote"` — lead MORNO, gerar orçamento
- `"transfer_to_closer"` — lead QUENTE, transferir para humano

**Como manter:** Para adicionar novos campos ao lead (ex: CPF para pessoa física), inclua em `LeadData` e atualize a lista de campos obrigatórios no `QUALIFIER_INSTRUCTIONS` em `qualifier_agent.py`.

---

### 3.3 `src/knowledge_builder.py`

**Responsabilidade:** Configurar e carregar a base de conhecimento RAG (Retrieval-Augmented Generation) com os documentos PDF da empresa.

#### Funções

**`get_knowledge_base() -> Knowledge`**

Cria e retorna uma instância `Knowledge` configurada, sem carregar ou indexar conteúdo. Utilizada pelos agentes para fazer buscas em tempo de execução.

Configuração interna:
- **Embedder:** `FastEmbedEmbedder` com modelo `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensões, suporte a português, roda localmente sem custo de API)
- **Vector DB:** `LanceDb` com `SearchType.hybrid` (combina busca vetorial semântica + busca por keyword BM25, via `tantivy`)
- **Tabela:** `steel_sales_knowledge`
- **Reader:** `PDFReader(split_on_pages=True, sanitize_content=True)` — cada página do PDF vira um chunk independente
- **max_results:** 5 chunks retornados por busca

**`load_knowledge_base(recreate: bool = False) -> Knowledge`**

Indexa todos os PDFs do diretório `knowledge/` no LanceDB. Deve ser executada manualmente pelo script `scripts/build_knowledge.py`.

| Parâmetro | Comportamento |
|---|---|
| `recreate=False` (padrão) | Indexação incremental — pula documentos que já existem na tabela |
| `recreate=True` | Apaga a tabela e reindexar tudo do zero |

**Como manter:**
- Para adicionar novos documentos: coloque o PDF em `knowledge/` e rode `python scripts/build_knowledge.py` (sem `--recreate` para indexação incremental).
- Para trocar o modelo de embedding: altere o `id` no `FastEmbedEmbedder` e ajuste `dimensions`. Execute `python scripts/build_knowledge.py --recreate` para reindexar.
- Para suportar outros formatos além de PDF: adicione um reader na dict `readers` (ex: `"docx": DocxReader()`).

---

### 3.4 `src/orchestrator.py`

**Responsabilidade:** Criar e configurar o `Team` do Agno que coordena os três agentes especializados.

#### Constante

**`ORCHESTRATOR_INSTRUCTIONS`** (string)

Prompt de sistema do orquestrador. Define:
1. O papel de coordenador entre os três agentes
2. O **formato obrigatório do bloco `---CONTEXTO ACUMULADO---`** que deve ser enviado a cada delegação — este bloco é o mecanismo central de manutenção de estado, porque os agentes membros não têm memória própria entre chamadas
3. A lógica de decisão sobre qual agente acionar:
   - Dados incompletos → Qualificador de Leads
   - Produto mencionado → Especialista de Produtos
   - Todos os dados coletados (MORNO) → Gerador de Orçamentos

#### Funções

**`create_steel_sales_team() -> Team`**

Factory que instancia e retorna o `Team` com todas as configurações.

Configurações relevantes do `Team`:

| Parâmetro | Valor | Efeito |
|---|---|---|
| `mode` | `"coordinate"` | O LLM do orquestrador decide qual agente chamar em cada turno |
| `db` | `SqliteDb(db_file="data/agent_sessions.db")` | Persiste histórico de mensagens em SQLite |
| `add_history_to_context` | `True` | O orquestrador recebe o histórico da sessão no contexto |
| `store_history_messages` | `True` | As mensagens são salvas no banco |
| `add_team_history_to_members` | `True` | Os agentes membros recebem o histórico quando são acionados |
| `num_team_history_runs` | `5` | Quantos turnos anteriores são injetados no contexto |
| `markdown` | `True` | Habilita formatação Markdown nas respostas |

**Como manter:**
- Para adicionar um novo agente ao time: crie o agente em `src/agents/`, importe em `orchestrator.py` e adicione na lista `members=[...]` do `Team`. Atualize o `ORCHESTRATOR_INSTRUCTIONS` para incluir o novo agente e sua lógica de delegação.
- Para aumentar o contexto histórico: incremente `num_team_history_runs`. Isso aumenta o uso de tokens por chamada.
- Para mudar o banco de sessão: substitua `SqliteDb` por outro `agno.db.*` (ex: PostgreSQL para ambientes de produção).

---

### 3.5 `src/agents/qualifier_agent.py`

**Responsabilidade:** Coletar os dados obrigatórios do lead de forma conversacional e classificá-lo como FRIO, MORNO ou QUENTE.

#### Constante

**`QUALIFIER_INSTRUCTIONS`** (string)

Define os critérios de classificação, os campos obrigatórios para MORNO, e o tom de voz (profissional, amigável, paciente). Instrui o agente a terminar toda resposta com:
```
STATUS: [FRIO|MORNO|QUENTE] - [motivo em uma linha]
```

#### Funções

**`create_qualifier_agent() -> Agent`**

Cria e retorna o agente `Qualificador de Leads` com:
- `knowledge=get_knowledge_base()` — acesso aos PDFs para consultar processo de qualificação
- `search_knowledge=True` — busca automática na knowledge base quando relevante

**Como manter:**
- Para adicionar/remover campos obrigatórios: edite `QUALIFIER_INSTRUCTIONS` na seção "Campos obrigatórios para MORNO".
- Para mudar os critérios de MORNO/QUENTE: edite as definições na mesma constante.

---

### 3.6 `src/agents/product_specialist_agent.py`

**Responsabilidade:** Traduzir a linguagem popular/coloquial do cliente para a nomenclatura técnica correta dos produtos de aço.

#### Constante

**`PRODUCT_SPECIALIST_INSTRUCTIONS`** (string)

Contém uma tabela de mapeamento (linguagem popular → nomenclatura técnica → categoria) e define o formato de resposta esperado com campos: produto técnico, categoria, especificações e frase de confirmação sugerida.

Exemplos de mapeamento:
| Cliente diz | Termo técnico | Categoria |
|---|---|---|
| Ferro, ferro de construção | Vergalhão | Construção Civil |
| Metalon | Tubo Quadrado/Retangular | Tubos |
| Telha de zinco | Telha Trapezoidal Galvanizada | Planos |
| L de ferro | Cantoneira | Serralheria |

#### Funções

**`create_product_specialist_agent() -> Agent`**

Cria e retorna o agente `Especialista de Produtos` com acesso à knowledge base para validar a nomenclatura técnica exata contra o catálogo de produtos em PDF.

**Como manter:**
- Para adicionar novos produtos: edite a tabela em `PRODUCT_SPECIALIST_INSTRUCTIONS`.
- A fonte de verdade final é o PDF `knowledge/dicionario_produtos.pdf` — o agente usa RAG para complementar a tabela no prompt.

---

### 3.7 `src/agents/quote_generator_agent.py`

**Responsabilidade:** Gerar um resumo estruturado do pedido quando o lead atingiu o status MORNO, preparando as informações para o Closer humano.

#### Constante

**`QUOTE_GENERATOR_INSTRUCTIONS`** (string)

Define o formato exato do resumo de orçamento (bloco textual com dados do cliente, pedido, status e próximos passos) e as regras de validação (verificar que todos os campos obrigatórios estão presentes antes de gerar).

#### Funções

**`create_quote_generator_agent() -> Agent`**

Cria e retorna o agente `Gerador de Orçamentos`. **Este é o único agente que não usa knowledge base**, pois opera apenas sobre os dados estruturados do lead já coletados.

**Como manter:**
- Para mudar o formato do resumo: edite `QUOTE_GENERATOR_INSTRUCTIONS`.
- Para integrar com um CRM ou sistema de tickets: adicione uma tool ao agente que faça o POST para o sistema externo ao gerar o resumo.

---

### 3.8 `src/api.py`

**Responsabilidade:** Expor o sistema de agentes via API REST com FastAPI, permitindo integração com WhatsApp (via Blip), sistemas CRM ou qualquer cliente HTTP.

#### Instância global

**`_team`** (variável module-level)

O `Team` é instanciado uma única vez e reutilizado em todas as requisições (padrão singleton via `get_team()`). Isso é necessário porque o Team carrega o estado da sessão do SQLite, e a criação de um novo Team a cada requisição perderia o histórico de conversas.

#### Funções

**`get_team() -> Team`**

Lazy initialization do singleton do Team. Cria o time na primeira chamada e reutiliza nas seguintes.

**`extract_classification(response_text: str) -> LeadClassification`**

Extrai a classificação do lead a partir do texto de resposta gerado pelos agentes, verificando a presença das palavras `QUENTE`, `MORNO` ou `FRIO` no texto (case-insensitive). Retorna `FRIO` como padrão se nenhuma palavra for encontrada.

**Limitação:** Esta extração é baseada em presença de palavras no texto livre. Se os agentes produzirem uma resposta ambígua (ex: mencionar "lead frio que agora está MORNO"), a detecção pode ser imprecisa. Para maior confiabilidade, considere usar structured output do LLM.

#### Endpoints

**`GET /health`**

Retorna `{"status": "ok", "service": "POC Agno Steel Agents"}`. Usado para health checks de load balancers ou monitoramento.

**`POST /chat`**

Recebe `IncomingMessage`, envia para o Team e retorna `AgentResponse`.

Fluxo interno:
1. Obtém o singleton do Team
2. Constrói o contexto: se `lead_data` foi fornecido, prefixa a mensagem com o JSON do lead para o orquestrador ter contexto adicional
3. Chama `team.run(context)` — chamada bloqueante (síncrona)
4. Extrai o texto da resposta via `.content` ou `str(response)`
5. Extrai a classificação via `extract_classification()`
6. Retorna `AgentResponse` estruturado

**Nota:** O endpoint `POST /chat` é `async def`, mas `team.run()` é síncrono. Em produção com alta carga, isso pode bloquear o event loop do uvicorn. Considere usar `asyncio.run_in_executor` para mover a chamada para uma thread pool.

**`GET /`**

Retorna a lista de endpoints disponíveis.

**Como manter:**
- Para adicionar autenticação: use `HTTPBearer` ou `OAuth2` do FastAPI como dependência nos endpoints.
- Para adicionar rate limiting: use o middleware `slowapi`.
- Para tornar o `/chat` verdadeiramente assíncrono: use `team.arun()` se disponível no Agno, ou `loop.run_in_executor(None, team.run, context)`.

---

### 3.9 `src/agent_os_server.py`

**Responsabilidade:** Expor os agentes e o time via AgentOS, que é o servidor de integração com o Agent UI — o frontend web do Agno para testar agentes visualmente.

#### Como usar

1. Inicie o servidor: `python src/agent_os_server.py` (porta 7777)
2. Em outro terminal: `npx create-agent-ui@latest` (porta 3001)
3. Abra `http://localhost:3001` e conecte em `http://localhost:7777`

#### Configuração

O `AgentOS` expõe tanto os **agentes individuais** quanto o **time completo**, permitindo testar cada agente isoladamente no UI ou usar o fluxo orquestrado completo.

`cors_allowed_origins` está configurado para `localhost:3000` e `localhost:3001` (padrão do Agent UI).

**Como manter:**
- Para adicionar um novo agente ao UI: instancie-o e adicione à lista `agents=[...]` do `AgentOS`.
- Para deploy em produção: ajuste `cors_allowed_origins` para os domínios corretos.

---

### 3.10 `scripts/build_knowledge.py`

**Responsabilidade:** Script de uso único (ou quando os PDFs mudarem) para indexar os documentos PDF na base vetorial LanceDB.

#### Uso

```bash
# Indexação incremental (pula o que já existe)
python scripts/build_knowledge.py

# Recriar do zero (apaga tabela e reindexar tudo)
python scripts/build_knowledge.py --recreate
```

**Quando rodar:**
- Primeira vez após clonar o repositório
- Quando um PDF novo for adicionado à pasta `knowledge/`
- Quando um PDF existente for atualizado (use `--recreate`)

**Como manter:**
- O script não aceita argumentos de path — sempre usa `knowledge/` e `data/lancedb/` conforme `config.py`. Se precisar de paths configuráveis, adicione argumentos ao `argparse`.

---

### 3.11 `scripts/demo_chat.py`

**Responsabilidade:** Interface de linha de comando (CLI) para testar o sistema interativamente, simulando uma conversa de WhatsApp.

#### Uso

```bash
python scripts/demo_chat.py
```

O script cria um `Team` e entra em loop de input/output no terminal. Útil para desenvolvimento e demonstração sem precisar subir a API REST.

**Como manter:**
- Para adicionar comandos especiais (ex: `/status` para ver o `LeadData` atual): adicione verificações ao `user_input` antes de chamar `team.run()`.

---

## 4. Dados e Persistência

### Estrutura de arquivos de dados

```
data/
├── lancedb/                      # Vector database (gerado automaticamente)
│   └── steel_sales_knowledge/    # Tabela LanceDB
│       ├── *.lance               # Arquivos de dados vetoriais
│       └── _latest.manifest      # Manifesto da tabela
└── agent_sessions.db             # SQLite com histórico de sessões
```

### Tabela de persistência

| Arquivo | Conteúdo | Gerado por | Lido por |
|---|---|---|---|
| `data/lancedb/` | Embeddings vetoriais dos chunks dos PDFs, índice híbrido (vetorial + BM25) | `scripts/build_knowledge.py` | `src/knowledge_builder.py` → agentes |
| `data/agent_sessions.db` | Histórico de mensagens das sessões (`runs`, `messages`, `sessions`), gerenciado pelo Agno via SQLAlchemy | `src/orchestrator.py` (Team) ao primeiro `team.run()` | `src/orchestrator.py` (Team) a cada chamada |
| `knowledge/*.pdf` | Documentos fonte: dicionário de produtos, processo de classificação de leads, estratégia de captação | Manuais (adicionados pela equipe comercial) | `scripts/build_knowledge.py` |

### PDFs da knowledge base

| PDF | Conteúdo esperado |
|---|---|
| `dicionario_produtos.pdf` | Catálogo técnico de produtos: nomenclatura oficial, especificações, categorias |
| `processo_classificacao.pdf` | Processo interno de qualificação: critérios FRIO/MORNO/QUENTE, campos obrigatórios |
| `estrategia_captacao.pdf` | Estratégias de prospecção e captação de leads |

### Ciclo de vida dos dados

```
PDFs atualizados
      │
      ▼ python scripts/build_knowledge.py [--recreate]
      │
data/lancedb/  ←──── indexados com FastEmbed (local, sem custo de API)
      │
      └── consultados em tempo real pelos agentes via search_knowledge

Conversa do usuário
      │
      ▼ team.run(mensagem)
      │
data/agent_sessions.db  ←──── histórico salvo automaticamente pelo Team
      │
      └── últimos 5 turnos injetados no contexto de cada delegação
```

---

## 5. Variáveis de Ambiente

Arquivo: `.env` (copie de `.env.example`)

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `GOOGLE_API_KEY` | Sim (se Gemini) | — | Chave de API do Google AI Studio para modelos Gemini |
| `ANTHROPIC_API_KEY` | Sim (se Claude) | — | Chave de API da Anthropic para modelos Claude |
| `MODEL_ID` | Não | `gemini-2.5-flash-preview-04-17` | ID do modelo LLM a usar |

### Modelos disponíveis

| MODEL_ID | Provedor | Característica | API Key necessária |
|---|---|---|---|
| `gemini-2.5-flash-preview-04-17` | Google | Rápido, econômico (padrão) | `GOOGLE_API_KEY` |
| `gemini-2.0-flash` | Google | Muito rápido | `GOOGLE_API_KEY` |
| `claude-haiku-4-5-20251001` | Anthropic | Econômico | `ANTHROPIC_API_KEY` |
| `claude-sonnet-4-6` | Anthropic | Balanceado (maior qualidade) | `ANTHROPIC_API_KEY` |

### Exemplo de `.env`

```dotenv
# Para usar Google Gemini (padrão)
GOOGLE_API_KEY=AIzaSy...

# Para usar Anthropic Claude (descomente as duas linhas abaixo)
# ANTHROPIC_API_KEY=sk-ant-...
# MODEL_ID=claude-haiku-4-5-20251001
```

---

## 6. Fluxo Completo de uma Conversa

Este exemplo mostra o ciclo completo desde a primeira mensagem até a geração do orçamento.

### Turno 1 — Primeiro contato (lead FRIO)

**Entrada (POST /chat):**
```json
{
  "session_id": "sess-whatsapp-5585999001122",
  "message": "Oi, quero comprar ferro"
}
```

**Processamento interno:**

1. `api.py`: recebe a mensagem, chama `team.run("Oi, quero comprar ferro")`
2. `orchestrator.py` (Team LLM): analisa a mensagem, não há dados do lead ainda → delega ao **Qualificador de Leads** com CONTEXTO ACUMULADO vazio
3. `qualifier_agent.py`: identifica que "ferro" pode ser vergalhão ou outro produto → pergunta mais informações, inicia coleta progressiva
4. Resposta retorna ao orquestrador → ao endpoint → ao cliente

**Saída:**
```json
{
  "session_id": "sess-whatsapp-5585999001122",
  "message": "Olá! Que bom falar com você! Para te ajudar melhor, preciso de algumas informações...\n\nPrimeiro, pode me dizer seu nome completo e o tipo de empresa que você representa?\n\nSTATUS: FRIO - Dados incompletos (nome, CNPJ, produto específico, volume não informados)",
  "classification": "FRIO",
  "lead_data": {"session_id": "sess-whatsapp-5585999001122", "classification": "FRIO", ...},
  "next_action": "collect_data"
}
```

### Turno 2 — Produto mencionado (delegação ao Especialista)

**Entrada:**
```json
{
  "session_id": "sess-whatsapp-5585999001122",
  "message": "Meu nome é João Silva, da construtora JBS. Preciso de metalon para estrutura"
}
```

**Processamento interno:**

1. `api.py` → `team.run(mensagem)`
2. `orchestrator.py`: carrega os 5 turnos anteriores do SQLite → `agent_sessions.db`, identifica "metalon" como produto → delega ao **Especialista de Produtos** com CONTEXTO ACUMULADO atualizado (Nome: João Silva)
3. `product_specialist_agent.py`: busca "metalon" na knowledge base (LanceDB) → retorna `Tubo Quadrado/Retangular`; em seguida, delega de volta ao Qualificador para continuar coleta
4. Orquestrador coordena a resposta composta

### Turno N — Todos os dados coletados (lead MORNO)

Quando o orquestrador identifica que todos os campos obrigatórios foram coletados:

**Delegação ao Gerador de Orçamentos com contexto:**
```
---CONTEXTO ACUMULADO---
Nome: João Silva
WhatsApp: (85) 99900-1122
E-mail: joao@jbs.com.br
CNPJ: 12.345.678/0001-99
UF: CE
Cidade: Fortaleza
Produto: Tubo Quadrado/Retangular (Metalon)
Volume: 500kg
Status atual: MORNO
Dados faltantes: []
---FIM DO CONTEXTO---
```

**Saída do Gerador de Orçamentos:**
```
═══════════════════════════════════
       RESUMO DO PEDIDO
═══════════════════════════════════

DADOS DO CLIENTE:
• Nome: João Silva
• CNPJ: 12.345.678/0001-99
• Contato: (85) 99900-1122 | joao@jbs.com.br
• Local: Fortaleza - CE
• Tipo: Construtora

PEDIDO:
• Produto: Tubo Quadrado/Retangular
• Volume: 500kg
• Urgência: não informado

STATUS: MORNO → Pronto para orçamento

PRÓXIMOS PASSOS:
→ Closer deve entrar em contato em até 2h
→ Apresentar tabela de preços atualizada
→ Confirmar disponibilidade em estoque

═══════════════════════════════════
```

**Resposta da API:**
```json
{
  "classification": "MORNO",
  "next_action": "generate_quote"
}
```

---

## 7. Classificação de Leads

| Status | Condição | `next_action` | Ação do sistema |
|---|---|---|---|
| `FRIO` | Um ou mais campos obrigatórios ausentes | `collect_data` | Continuar coletando informações |
| `MORNO` | Todos os 8 campos obrigatórios preenchidos | `generate_quote` | Gerar resumo para o Closer |
| `QUENTE` | Orçamento gerado e enviado ao Closer | `transfer_to_closer` | Notificar equipe comercial |

**Campos obrigatórios para MORNO:**
Nome · WhatsApp · E-mail · CNPJ · UF · Cidade · Produto · Volume estimado

---

## 8. Como Rodar

### Pré-requisitos

- Python 3.11+
- Conta Google AI Studio ou Anthropic (dependendo do modelo escolhido)

### Setup inicial

```bash
# 1. Clonar e instalar dependências
git clone <repo>
cd POC-Agno-RAG
pip install -e .

# 2. Configurar API key
cp .env.example .env
# Editar .env: adicionar GOOGLE_API_KEY ou ANTHROPIC_API_KEY

# 3. Indexar os PDFs na knowledge base (executar uma única vez)
python scripts/build_knowledge.py
```

### Formas de execução

```bash
# Demo interativo no terminal (mais simples para testar)
python scripts/demo_chat.py

# API REST (para integração com WhatsApp/Blip)
uvicorn src.api:app --reload
# Acesse a documentação em: http://localhost:8000/docs

# Agent UI (interface web visual)
python src/agent_os_server.py
# Em outro terminal:
npx create-agent-ui@latest
# Abra http://localhost:3001 e conecte em http://localhost:7777
```

### Testar a API manualmente

```bash
# Health check
curl http://localhost:8000/health

# Enviar mensagem
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-001", "message": "Olá, quero comprar vergalhão"}'
```

---

## 9. Testes

### Suites de testes disponíveis

| Arquivo | Escopo | Requer API key |
|---|---|---|
| `tests/test_orchestrator.py` | Estrutura do Team, configuração de sessão | Não |
| `tests/test_qualifier_agent.py` | Agente qualificador, campos obrigatórios | Sim (LLM call) |
| `tests/test_product_specialist_agent.py` | Tradução de produtos | Sim (LLM call) |
| `tests/test_quote_generator_agent.py` | Geração de resumo | Sim (LLM call) |
| `tests/test_api.py` | Endpoints FastAPI | Sim (LLM call) |
| `tests/test_business_scenarios.py` | Cenários de negócio end-to-end | Sim (LLM call) |

### Comandos

```bash
# Testes estruturais (sem API key — rápidos)
pytest tests/ -v -k "not test_classify_incomplete_lead_as_frio"

# Todos os testes (requer API key configurada)
pytest tests/ -v

# Teste específico
pytest tests/test_orchestrator.py -v
```

---

## 10. Dependências

| Pacote | Versão mínima | Uso |
|---|---|---|
| `agno` | 2.5.3 | Framework multi-agent (Team, Agent, Knowledge) |
| `google-genai` | 1.0.0 | SDK do Google Gemini |
| `anthropic` | 0.40.0 | SDK do Anthropic Claude |
| `fastapi` | 0.115.0 | API REST |
| `uvicorn` | 0.32.0 | Servidor ASGI para FastAPI |
| `python-dotenv` | 1.0.0 | Carregamento do `.env` |
| `pypdf` | 5.0.0 | Leitura de PDFs (usado internamente pelo Agno PDFReader) |
| `lancedb` | 0.13.0 | Vector database local |
| `pylance` | 2.0.0 | Driver LanceDB |
| `tantivy` | 0.22.0 | Índice de busca BM25 (usado pelo hybrid search do LanceDB) |
| `fastembed` | 0.7.0 | Embeddings locais ONNX (sem custo de API) |
| `pydantic` | 2.0.0 | Modelos de dados e validação |
| `sqlalchemy` | 2.0.0 | ORM usado pelo Agno para o SQLite de sessões |
| `pytest` | 8.0.0 | Testes |
| `pytest-asyncio` | 0.23.0 | Suporte a testes assíncronos |

---

## 11. Como Escalar e Manter

### Adicionar um novo agente especializado

1. Crie `src/agents/nome_agente.py` seguindo o padrão dos existentes:
   ```python
   from agno.agent import Agent
   from src.config import get_model

   INSTRUCOES = "..."

   def create_nome_agent() -> Agent:
       return Agent(name="...", model=get_model(), instructions=INSTRUCOES, ...)
   ```
2. Importe e adicione ao `members=[...]` em `src/orchestrator.py`
3. Atualize `ORCHESTRATOR_INSTRUCTIONS` com a lógica de delegação
4. Adicione ao `src/agent_os_server.py` se quiser testar no UI
5. Crie `tests/test_nome_agent.py`

### Substituir o banco de sessões por PostgreSQL (produção)

```python
# Em src/orchestrator.py, substitua:
from agno.db.sqlite import SqliteDb
db=SqliteDb(db_file="data/agent_sessions.db")

# Por:
from agno.db.postgresql import PostgresDb
db=PostgresDb(connection_string=os.getenv("DATABASE_URL"))
```

### Adicionar novos documentos à knowledge base

```bash
# 1. Copie o PDF para a pasta knowledge/
cp novo_catalogo.pdf knowledge/

# 2. Indexe de forma incremental (não apaga os existentes)
python scripts/build_knowledge.py
```

### Trocar o modelo LLM

```bash
# Apenas altere MODEL_ID no .env — nenhuma mudança de código necessária
MODEL_ID=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...
```

### Monitoramento e observabilidade

O Agno 2.5.3 suporta integração nativa com o **Agno Platform** para rastreamento de sessões, tokens e performance. Para ativar, configure `AGNO_API_KEY` no `.env` (ver documentação oficial em https://docs.agno.com).

Para monitoramento básico de produção sem o Agno Platform:
- Os logs de cada `team.run()` incluem qual agente foi acionado e o conteúdo das delegações
- O SQLite `data/agent_sessions.db` pode ser consultado diretamente para auditoria de conversas

### Considerações de produção

| Ponto | Situação atual (POC) | Recomendação para produção |
|---|---|---|
| Banco de sessões | SQLite local | PostgreSQL ou MySQL |
| Vector DB | LanceDB local | LanceDB com armazenamento em S3 ou Qdrant/Pinecone |
| API concorrência | `team.run()` síncrono bloqueante | Usar `run_in_executor` ou workers múltiplos |
| Autenticação | Sem autenticação | JWT ou API Key no header |
| Identificação de sessão | `session_id` livre | Vincular ao ID do usuário do WhatsApp |
| Secrets | `.env` local | Vault, AWS Secrets Manager ou variáveis do ambiente de deploy |
