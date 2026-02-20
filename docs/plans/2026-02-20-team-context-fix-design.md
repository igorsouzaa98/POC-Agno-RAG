# Design: Correção de Contexto no Agno Team

**Data:** 2026-02-20
**Problema:** O Team perde o histórico da conversa entre turns, fazendo o agente reiniciar a coleta de dados do zero.

## Causa Raiz

Em `mode="coordinate"`, o Team (orquestrador) delega tarefas via `DELEGATE_TASK_TO_MEMBER`. Sem session storage, cada turn do orquestrador começa sem memória das mensagens anteriores. O membro recebe apenas o task description atual — sem saber o que já foi coletado.

## Solução

### 1. Session Storage no Team (SqliteDb)
Adicionar `db=SqliteDb(db_file="data/agent_sessions.db")` ao Team. O Agno persiste automaticamente o histórico de cada `session_id` no SQLite.

### 2. Histórico no contexto do orquestrador
Ativar `add_history_to_context=True` e `store_history_messages=True` para que o orquestrador veja as mensagens anteriores ao processar cada novo turn.

### 3. Histórico repassado aos membros
Ativar `add_team_history_to_members=True` com `num_team_history_runs=5`. Assim, quando o orquestrador delega, o membro recebe o histórico do team junto com o task — evitando que reinicie a coleta.

### 4. Reescrever instruções do orquestrador
Adicionar seção explícita nas `ORCHESTRATOR_INSTRUCTIONS` exigindo que cada delegação inclua um bloco **"CONTEXTO ACUMULADO"** listando todos os dados já coletados, o que ainda falta, e o status atual do lead.

## Arquivos a modificar

| Arquivo | Mudança |
|---------|---------|
| `src/orchestrator.py` | Adicionar `db`, `add_history_to_context`, `store_history_messages`, `add_team_history_to_members`; reescrever instruções |
| `pyproject.toml` | Adicionar `sqlalchemy>=2.0.0` |

## O que NÃO muda
- Arquitetura multi-agent (Team + 3 agentes membros) — mantida
- Agentes membros individuais — sem alteração
- `agent_os_server.py` — sem alteração
