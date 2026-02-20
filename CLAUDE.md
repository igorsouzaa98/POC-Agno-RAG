# POC Agno Steel Agents

## Contexto
POC de agentes de IA com Agno 2.5.3 para automatizar atendimento de leads de uma distribuidora de produtos de aço.

## Comandos principais
- `pytest tests/ -v` — Todos os testes
- `pytest tests/ -v -k "not test_classify_incomplete_lead_as_frio"` — Sem API key
- `python scripts/demo_chat.py` — Demo interativo (requer API key)
- `python scripts/build_knowledge.py` — Reindexar PDFs
- `uvicorn src.api:app --reload` — Iniciar API

## Modelo
- `claude-haiku-4-5-20251001` (configurado em src/config.py e .env)

## Agno 2.5.3 - API relevante
- `Knowledge` (não `PDFKnowledgeBase`) em `agno.knowledge.knowledge`
- `FastEmbedEmbedder` para embeddings locais (multilingual)
- `Team(mode="coordinate")` para orquestração
- `agent.run(msg)` retorna objeto com `.content`

## Estrutura
- `src/agents/` — 3 agentes especializados
- `src/orchestrator.py` — Agno Team coordenando os agentes
- `src/knowledge_builder.py` — RAG com FastEmbed + LanceDB
- `knowledge/` — PDFs da empresa já indexados
