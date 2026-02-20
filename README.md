# POC Agno - Agentes de IA para Atendimento de Vendas de Aço

## Visão Geral

Sistema multi-agente usando o framework [Agno](https://docs.agno.com) (v2.5.3) com Claude Haiku 4.5 (Anthropic) para automatizar o fluxo de atendimento e qualificação de leads de uma distribuidora de produtos de aço.

## Arquitetura

```
Lead (WhatsApp/Blip)
    ↓
FastAPI (POST /chat)
    ↓
Agno Team - Orquestrador (modo: coordinate)
    ├─ Qualificador de Leads → Classifica: FRIO | MORNO | QUENTE
    ├─ Especialista de Produtos → Traduz terminologia técnica
    └─ Gerador de Orçamentos → Prepara resumo para Closer
    ↓
Resposta + Classificação do Lead
```

## Classificação de Leads

| Status | Condição | Próxima Ação |
|--------|----------|--------------|
| **FRIO** | Dados incompletos (falta nome, CNPJ, produto, volume, etc.) | Coletar informações progressivamente |
| **MORNO** | Todos os dados obrigatórios coletados | Gerar resumo de orçamento |
| **QUENTE** | Orçamento gerado e passado ao Closer | Notificar equipe comercial |

## Campos Obrigatórios para MORNO

Nome · WhatsApp · E-mail · CNPJ (válido) · UF · Cidade · Produto · Volume estimado

## Produtos Suportados

| Popular | Técnico | Categoria |
|---------|---------|-----------|
| Ferro para laje | Vergalhão SI 50 | Construção Civil |
| Ferro de coluna | Vergalhão CA 60 | Construção Civil |
| Metalon | Tubo Quadrado/Retangular | Tubos |
| Telha de zinco | Telha Trapezoidal Galvanizada | Planos |
| L de ferro | Cantoneira | Serralheria |

## Setup

### 1. Instalar dependências
```bash
pip install -e .
```

### 2. Configurar API Key
```bash
cp .env.example .env
# Editar .env e colocar sua ANTHROPIC_API_KEY
```

### 3. Indexar a knowledge base (uma vez)
```bash
python scripts/build_knowledge.py
```

### 4. Rodar demo interativo
```bash
python scripts/demo_chat.py
```

### 5. Iniciar API
```bash
uvicorn src.api:app --reload
# Acesse: http://localhost:8000/docs
```

## Testes

```bash
# Testes estruturais (sem API key necessária)
pytest tests/ -v -k "not test_classify_incomplete_lead_as_frio"

# Todos os testes (requer ANTHROPIC_API_KEY)
pytest tests/ -v
```

## Estrutura do Projeto

```
poc-agno-steel-agents/
├── knowledge/                    # PDFs indexados para RAG
│   ├── dicionario_produtos.pdf
│   ├── processo_classificacao.pdf
│   └── estrategia_captacao.pdf
├── data/
│   └── lancedb/                  # Vector DB local (FastEmbed)
├── src/
│   ├── config.py                 # Configurações e MODEL_ID
│   ├── models.py                 # Modelos Pydantic
│   ├── knowledge_builder.py      # Configuração do RAG
│   ├── orchestrator.py           # Agno Team (coordenação)
│   ├── api.py                    # FastAPI endpoints
│   └── agents/
│       ├── qualifier_agent.py    # Qualificador FRIO/MORNO/QUENTE
│       ├── product_specialist_agent.py  # Tradutor de produtos
│       └── quote_generator_agent.py     # Gerador de resumos
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
├── pyproject.toml
└── .env.example
```

## Tecnologias

- **[Agno](https://docs.agno.com)** v2.5.3 — Framework multi-agent
- **Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) — LLM principal
- **FastEmbed** — Embeddings locais multilingual (sem custo de API)
- **LanceDB** — Vector database local
- **FastAPI** — Interface de teste/integração
- **Pydantic v2** — Validação de dados

## Exemplo de Uso (API)

```bash
# Verificar saúde da API
curl http://localhost:8000/health

# Enviar mensagem para os agentes
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "sess-001", "message": "Olá, quero comprar vergalhão"}'
```
