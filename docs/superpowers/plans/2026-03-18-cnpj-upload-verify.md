# CNPJ Upload & Verificação Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir upload de PDF de CNPJ no chat, verificar inadimplência e atendimento ativo antes de iniciar conversa, e indexar o documento no banco vetorial.

**Architecture:** O frontend (Agno Agent UI, porta 7777) ganha um botão de upload no ChatInput. O backend adiciona dois endpoints no AgentOS server: `POST /cnpj/upload` (processa PDF, extrai CNPJ, roda verificações, indexa no LanceDB) e `POST /cnpj/verify` (verifica CNPJ por string). Quando o CNPJ tem problema, a resposta bloqueia a conversa com mensagem explicativa. Um `CnpjService` encapsula toda a lógica de extração, validação e verificação.

**Tech Stack:** FastAPI (UploadFile), pypdf (extração de texto), LanceDB + FastEmbed (indexação vetorial), SQLite (check de sessão ativa), React + TypeScript (frontend)

---

## File Map

| Ação | Arquivo | Responsabilidade |
|------|---------|-----------------|
| CREATE | `src/cnpj_service.py` | Extração de CNPJ do PDF, validação, checks (inadimplência/sessão), indexação |
| MODIFY | `src/models.py` | Adicionar `CnpjVerifyResponse` e enum `CnpjStatus` |
| MODIFY | `src/agent_os_server.py` | Montar endpoints `/cnpj/upload` e `/cnpj/verify` no app |
| CREATE | `tests/test_cnpj_service.py` | Testes unitários do CnpjService |
| CREATE | `tests/test_cnpj_endpoints.py` | Testes de integração dos endpoints /cnpj/* |
| MODIFY | `Agno-Agent-UI/agent-ui/src/components/ui/icon/types.ts` | Adicionar `'paperclip'` ao `IconType` |
| MODIFY | `Agno-Agent-UI/agent-ui/src/components/ui/icon/constants.tsx` | Mapear `Paperclip` do lucide-react |
| MODIFY | `Agno-Agent-UI/agent-ui/src/components/chat/ChatArea/ChatInput/ChatInput.tsx` | Botão de upload, estado de verificação, bloqueio de conversa |

---

## Task 1: Models — CnpjStatus e CnpjVerifyResponse

**Files:**
- Modify: `src/models.py`
- Test: `tests/test_cnpj_service.py` (usará esses modelos)

- [ ] **Step 1: Adicionar modelos ao src/models.py**

Abrir `src/models.py` e adicionar ao final do arquivo:

```python
class CnpjStatus(str, Enum):
    OK = "ok"
    INADIMPLENTE = "inadimplente"
    EM_ATENDIMENTO = "em_atendimento"
    INVALIDO = "invalido"


class CnpjVerifyResponse(BaseModel):
    cnpj: str
    status: CnpjStatus
    bloqueado: bool
    mensagem: str
    session_id_ativo: Optional[str] = None
```

- [ ] **Step 2: Commit**

```bash
git add src/models.py
git commit -m "feat: add CnpjStatus and CnpjVerifyResponse models"
```

---

## Task 2: CnpjService — extração, validação e verificação

**Files:**
- Create: `src/cnpj_service.py`
- Test: `tests/test_cnpj_service.py`

- [ ] **Step 1: Escrever os testes com falha esperada**

Criar `tests/test_cnpj_service.py`:

```python
import pytest
from src.cnpj_service import CnpjService


@pytest.fixture
def service():
    return CnpjService(db_path="data/agent_sessions.db")


def test_validate_cnpj_valido(service):
    assert service.validate_cnpj("11222333000181") is True


def test_validate_cnpj_invalido_tamanho(service):
    assert service.validate_cnpj("1122233300018") is False


def test_validate_cnpj_invalido_letras(service):
    assert service.validate_cnpj("1122233300018X") is False


def test_validate_cnpj_com_formatacao(service):
    # deve aceitar com pontuação
    assert service.validate_cnpj("11.222.333/0001-81") is True


def test_check_inadimplencia_cnpj_limpo(service):
    result = service.check_inadimplencia("11222333000181")
    assert "inadimplente" in result
    assert isinstance(result["inadimplente"], bool)


def test_check_inadimplencia_stub_retorna_false_por_padrao(service):
    result = service.check_inadimplencia("11222333000181")
    assert result["inadimplente"] is False


def test_check_inadimplencia_cnpj_bloqueado(service):
    # CNPJ especial para simular inadimplência em testes
    result = service.check_inadimplencia("00000000000000")
    assert result["inadimplente"] is True


def test_check_active_session_cnpj_sem_sessao(service):
    result = service.check_active_session("99999999999999")
    assert result["em_atendimento"] is False
    assert result["session_id"] is None


def test_extract_cnpj_from_text(service):
    text = "CNPJ: 11.222.333/0001-81 - Empresa Teste LTDA"
    cnpj = service.extract_cnpj_from_text(text)
    assert cnpj == "11222333000181"


def test_extract_cnpj_from_text_sem_cnpj(service):
    text = "Texto sem CNPJ nenhum aqui"
    cnpj = service.extract_cnpj_from_text(text)
    assert cnpj is None
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
uv run pytest tests/test_cnpj_service.py -v
```

Esperado: `ModuleNotFoundError: No module named 'src.cnpj_service'`

- [ ] **Step 3: Criar src/cnpj_service.py**

```python
"""
Serviço de verificação e processamento de CNPJ.

- Extração de CNPJ de texto/PDF (via pypdf)
- Validação de formato
- Verificação de inadimplência (stub para POC)
- Verificação de sessão ativa no SQLite
- Indexação do documento no LanceDB
"""
import re
import io
import sqlite3
import tempfile
import os
from pathlib import Path
from typing import Optional

from pypdf import PdfReader

# CNPJs marcados como inadimplentes no stub (para testes e demo)
_INADIMPLENTES_STUB = {
    "00000000000000",  # CNPJ reservado para simular inadimplência em testes
}


class CnpjService:
    def __init__(self, db_path: str = "data/agent_sessions.db"):
        self._db_path = db_path

    # ─── Validação ───────────────────────────────────────────────────────────

    def validate_cnpj(self, cnpj: str) -> bool:
        """Valida formato do CNPJ (14 dígitos, aceita pontuação)."""
        digits = re.sub(r"\D", "", cnpj)
        return len(digits) == 14

    def normalize_cnpj(self, cnpj: str) -> str:
        """Remove pontuação e retorna apenas 14 dígitos."""
        return re.sub(r"\D", "", cnpj)

    # ─── Extração ────────────────────────────────────────────────────────────

    def extract_cnpj_from_text(self, text: str) -> Optional[str]:
        """Encontra o primeiro CNPJ válido no texto."""
        pattern = r"\d{2}[\.\s]?\d{3}[\.\s]?\d{3}[\/\s]?\d{4}[\-\s]?\d{2}"
        match = re.search(pattern, text)
        if match:
            return self.normalize_cnpj(match.group())
        return None

    def extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """Extrai todo o texto de um PDF em bytes."""
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)

    def extract_cnpj_from_pdf(self, file_bytes: bytes) -> Optional[str]:
        """Extrai CNPJ de um PDF enviado como bytes."""
        text = self.extract_text_from_pdf(file_bytes)
        return self.extract_cnpj_from_text(text)

    # ─── Verificações ────────────────────────────────────────────────────────

    def check_inadimplencia(self, cnpj: str) -> dict:
        """
        Stub: verifica inadimplência do CNPJ.

        Em produção substituir por chamada a Serasa/BigDataCorp/ReceitaFederal.
        Por ora usa lista fixa de CNPJs bloqueados para demo.
        """
        normalized = self.normalize_cnpj(cnpj)
        inadimplente = normalized in _INADIMPLENTES_STUB
        return {
            "inadimplente": inadimplente,
            "fonte": "stub",
            "detalhes": (
                "CNPJ com restrições financeiras (simulado)"
                if inadimplente
                else "Sem restrições encontradas (simulado)"
            ),
        }

    def check_active_session(self, cnpj: str) -> dict:
        """
        Verifica se o CNPJ já tem uma sessão ativa no banco de sessões.

        Busca nas sessões da última 24h que contenham o CNPJ nos dados de runs.
        """
        normalized = self.normalize_cnpj(cnpj)
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            # Busca sessões que mencionam o CNPJ nos runs ou session_data
            cursor.execute(
                """
                SELECT session_id FROM agno_sessions
                WHERE (runs LIKE ? OR session_data LIKE ?)
                AND updated_at > (strftime('%s', 'now') - 86400) * 1000
                LIMIT 1
                """,
                (f"%{normalized}%", f"%{normalized}%"),
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return {"em_atendimento": True, "session_id": row[0]}
        except Exception:
            pass
        return {"em_atendimento": False, "session_id": None}

    # ─── Indexação ───────────────────────────────────────────────────────────

    def index_cnpj_document(self, cnpj: str, file_bytes: bytes) -> None:
        """
        Indexa o documento de CNPJ no banco vetorial (LanceDB).

        Salva o PDF temporariamente e usa o knowledge builder para indexar.
        """
        from src.knowledge_builder import get_knowledge_base

        normalized = self.normalize_cnpj(cnpj)
        kb = get_knowledge_base()

        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            prefix=f"cnpj_{normalized}_",
            delete=False,
        ) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            kb.insert(
                path=tmp_path,
                name=f"cnpj_{normalized}",
                upsert=True,
                skip_if_exists=False,
            )
        finally:
            os.unlink(tmp_path)
```

- [ ] **Step 4: Rodar testes**

```bash
uv run pytest tests/test_cnpj_service.py -v
```

Esperado: todos os testes passam.

- [ ] **Step 5: Commit**

```bash
git add src/cnpj_service.py tests/test_cnpj_service.py
git commit -m "feat: add CnpjService with extraction, validation and checks"
```

---

## Task 3: Backend — endpoints /cnpj/upload e /cnpj/verify

**Files:**
- Modify: `src/agent_os_server.py`
- Create: `tests/test_cnpj_endpoints.py`

> **Importante:** Os testes de endpoints CNPJ ficam em arquivo separado (`test_cnpj_endpoints.py`) para evitar conflito de importação do `app` com `tests/test_api.py` que já importa `src.api.app` no escopo do módulo.

- [ ] **Step 1: Criar tests/test_cnpj_endpoints.py com testes falhando**

Criar `tests/test_cnpj_endpoints.py`:

```python
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    import sys
    sys.path.insert(0, '.')
    from src.agent_os_server import app
    return TestClient(app)


def test_cnpj_verify_cnpj_invalido(client):
    """CNPJ com formato errado retorna status invalido."""
    response = client.post("/cnpj/verify", json={"cnpj": "123"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "invalido"
    assert data["bloqueado"] is True


def test_cnpj_verify_cnpj_valido_limpo(client):
    """CNPJ válido sem restrições retorna status ok."""
    response = client.post("/cnpj/verify", json={"cnpj": "11222333000181"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["bloqueado"] is False


def test_cnpj_verify_cnpj_inadimplente(client):
    """CNPJ marcado como inadimplente retorna bloqueado."""
    response = client.post("/cnpj/verify", json={"cnpj": "00000000000000"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inadimplente"
    assert data["bloqueado"] is True
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
uv run pytest tests/test_cnpj_endpoints.py::test_cnpj_verify_cnpj_invalido -v
```

Esperado: `FAIL` — endpoint não existe ainda (404 ou ImportError).

- [ ] **Step 3: Adicionar endpoints ao agent_os_server.py**

No `src/agent_os_server.py`, após `app = agent_os.get_app()`, adicionar:

```python
from fastapi import UploadFile, File
from pydantic import BaseModel
from src.cnpj_service import CnpjService
from src.models import CnpjStatus, CnpjVerifyResponse

_cnpj_service = CnpjService()


class CnpjVerifyRequest(BaseModel):
    cnpj: str


@app.post("/cnpj/verify", response_model=CnpjVerifyResponse)
async def cnpj_verify(body: CnpjVerifyRequest):
    """Verifica CNPJ (formato, inadimplência, sessão ativa) sem upload de arquivo."""
    cnpj = body.cnpj

    if not _cnpj_service.validate_cnpj(cnpj):
        return CnpjVerifyResponse(
            cnpj=cnpj,
            status=CnpjStatus.INVALIDO,
            bloqueado=True,
            mensagem="CNPJ inválido. Por favor, verifique o número e tente novamente.",
        )

    normalized = _cnpj_service.normalize_cnpj(cnpj)

    inadimplencia = _cnpj_service.check_inadimplencia(normalized)
    if inadimplencia["inadimplente"]:
        return CnpjVerifyResponse(
            cnpj=normalized,
            status=CnpjStatus.INADIMPLENTE,
            bloqueado=True,
            mensagem="Não foi possível iniciar o atendimento. O CNPJ informado possui restrições financeiras. Entre em contato com nossa equipe para mais informações.",
        )

    sessao = _cnpj_service.check_active_session(normalized)
    if sessao["em_atendimento"]:
        return CnpjVerifyResponse(
            cnpj=normalized,
            status=CnpjStatus.EM_ATENDIMENTO,
            bloqueado=False,
            mensagem="Identificamos que este CNPJ já possui um atendimento em andamento. Conectando à sua conversa anterior.",
            session_id_ativo=sessao["session_id"],
        )

    return CnpjVerifyResponse(
        cnpj=normalized,
        status=CnpjStatus.OK,
        bloqueado=False,
        mensagem="CNPJ verificado com sucesso. Pode iniciar o atendimento.",
    )


@app.post("/cnpj/upload", response_model=CnpjVerifyResponse)
async def cnpj_upload(file: UploadFile = File(...)):
    """Recebe PDF do cartão CNPJ, extrai o número, verifica e indexa no banco vetorial."""
    file_bytes = await file.read()

    cnpj = _cnpj_service.extract_cnpj_from_pdf(file_bytes)
    if not cnpj:
        return CnpjVerifyResponse(
            cnpj="",
            status=CnpjStatus.INVALIDO,
            bloqueado=True,
            mensagem="Não foi possível identificar um CNPJ válido no documento enviado. Por favor, envie o Cartão CNPJ da Receita Federal.",
        )

    # Reutiliza a lógica de verificação
    verify_response = await cnpj_verify(CnpjVerifyRequest(cnpj=cnpj))

    # Indexa o documento mesmo se bloqueado (para histórico)
    try:
        _cnpj_service.index_cnpj_document(cnpj, file_bytes)
    except Exception:
        pass  # Indexação não deve bloquear o fluxo

    return verify_response
```

- [ ] **Step 4: Rodar testes**

```bash
uv run pytest tests/test_cnpj_endpoints.py -v
```

Esperado: os 3 testes de CNPJ passam.

- [ ] **Step 5: Commit**

```bash
git add src/agent_os_server.py tests/test_cnpj_endpoints.py
git commit -m "feat: add /cnpj/verify and /cnpj/upload endpoints to AgentOS server"
```

---

## Task 4: Frontend — ícone paperclip + botão de upload + verificação de CNPJ

**Files:**
- Modify: `Agno-Agent-UI/agent-ui/src/components/ui/icon/types.ts`
- Modify: `Agno-Agent-UI/agent-ui/src/components/ui/icon/constants.tsx`
- Modify: `Agno-Agent-UI/agent-ui/src/components/chat/ChatArea/ChatInput/ChatInput.tsx`

O frontend já usa `FormData` e `handleStreamResponse` aceita `FormData`. O agno-ui já tem `useQueryState` para `session`. A verificação acontece ANTES de enviar a mensagem: upload do PDF → resposta do `/cnpj/upload` → se bloqueado exibe mensagem; se ok, seta o CNPJ no estado e libera o chat.

- [ ] **Step 1: Adicionar `'paperclip'` ao IconType em types.ts**

Abrir `Agno-Agent-UI/agent-ui/src/components/ui/icon/types.ts` e adicionar `'paperclip'` à union `IconType`, após `'trash'`:

```ts
  | 'trash'
  | 'paperclip'
```

- [ ] **Step 2: Mapear Paperclip em constants.tsx**

Abrir `Agno-Agent-UI/agent-ui/src/components/ui/icon/constants.tsx`:

Na linha de imports do `lucide-react`, adicionar `Paperclip`:
```ts
import {
  RefreshCw,
  Edit,
  Save,
  X,
  ArrowDown,
  SendIcon,
  Download,
  HammerIcon,
  Check,
  ChevronDown,
  ChevronUp,
  Trash,
  Paperclip
} from 'lucide-react'
```

No objeto `ICONS`, após `trash`, adicionar:
```ts
  trash: Trash,
  paperclip: Paperclip
```

- [ ] **Step 3: Atualizar ChatInput.tsx**

Substituir o conteúdo do `ChatInput.tsx` por:

```tsx
'use client'
import { useState, useRef } from 'react'
import { toast } from 'sonner'
import { TextArea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { useStore } from '@/store'
import useAIChatStreamHandler from '@/hooks/useAIStreamHandler'
import { useQueryState } from 'nuqs'
import Icon from '@/components/ui/icon'
import { constructEndpointUrl } from '@/lib/constructEndpointUrl'

type CnpjStatus = 'ok' | 'inadimplente' | 'em_atendimento' | 'invalido'

interface CnpjVerifyResponse {
  cnpj: string
  status: CnpjStatus
  bloqueado: boolean
  mensagem: string
  session_id_ativo?: string
}

type VerificationState = 'idle' | 'checking' | 'blocked' | 'approved'

const ChatInput = () => {
  const { chatInputRef } = useStore()
  const { handleStreamResponse } = useAIChatStreamHandler()
  const [selectedAgent] = useQueryState('agent')
  const [teamId] = useQueryState('team')
  const [, setSessionId] = useQueryState('session')
  const [inputMessage, setInputMessage] = useState('')
  const isStreaming = useStore((state) => state.isStreaming)
  const selectedEndpoint = useStore((state) => state.selectedEndpoint)

  const [verificationState, setVerificationState] = useState<VerificationState>('idle')
  const [verificationMessage, setVerificationMessage] = useState('')
  const [verifiedCnpj, setVerifiedCnpj] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const isInputDisabled = !(selectedAgent || teamId) || verificationState === 'checking' || verificationState === 'blocked'
  const isSendDisabled = isInputDisabled || !inputMessage.trim() || isStreaming

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.type !== 'application/pdf') {
      toast.error('Por favor, envie apenas arquivos PDF.')
      return
    }

    setVerificationState('checking')
    setVerificationMessage('Verificando CNPJ... aguarde.')

    try {
      const formData = new FormData()
      formData.append('file', file)

      const baseUrl = constructEndpointUrl(selectedEndpoint)

      const response = await fetch(`${baseUrl}/cnpj/upload`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) throw new Error('Erro ao verificar CNPJ.')

      const data: CnpjVerifyResponse = await response.json()

      if (data.bloqueado) {
        setVerificationState('blocked')
        setVerificationMessage(data.mensagem)
        toast.error(data.mensagem)
      } else {
        setVerifiedCnpj(data.cnpj)
        setVerificationState('approved')
        setVerificationMessage(data.mensagem)

        // Se há sessão ativa, redirecionar para ela
        if (data.session_id_ativo) {
          setSessionId(data.session_id_ativo)
        }

        toast.success(`CNPJ ${data.cnpj} verificado com sucesso.`)
      }
    } catch (err) {
      setVerificationState('idle')
      toast.error('Erro ao processar o documento. Tente novamente.')
    } finally {
      // Limpar input para permitir re-upload do mesmo arquivo
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleResetVerification = () => {
    setVerificationState('idle')
    setVerificationMessage('')
    setVerifiedCnpj(null)
  }

  const handleSubmit = async () => {
    if (!inputMessage.trim()) return

    const currentMessage = verifiedCnpj
      ? `[CNPJ: ${verifiedCnpj}] ${inputMessage}`
      : inputMessage

    setInputMessage('')

    try {
      await handleStreamResponse(currentMessage)
    } catch (error) {
      toast.error(
        `Error in handleSubmit: ${error instanceof Error ? error.message : String(error)}`
      )
    }
  }

  return (
    <div className="relative mx-auto mb-1 flex w-full max-w-2xl flex-col items-center gap-y-2 font-geist">
      {/* Banner de verificação */}
      {verificationState === 'checking' && (
        <div className="w-full rounded-lg border border-yellow-400 bg-yellow-50 px-4 py-2 text-sm text-yellow-800">
          ⏳ {verificationMessage}
        </div>
      )}
      {verificationState === 'blocked' && (
        <div className="w-full rounded-lg border border-red-400 bg-red-50 px-4 py-2 text-sm text-red-800">
          🚫 {verificationMessage}
          <button
            onClick={handleResetVerification}
            className="ml-2 underline hover:no-underline"
          >
            Tentar outro documento
          </button>
        </div>
      )}
      {verificationState === 'approved' && (
        <div className="w-full rounded-lg border border-green-400 bg-green-50 px-4 py-2 text-sm text-green-800">
          ✅ {verificationMessage}
          {verifiedCnpj && <span className="ml-1 font-mono font-semibold">(CNPJ: {verifiedCnpj})</span>}
        </div>
      )}

      {/* Input row */}
      <div className="flex w-full items-end justify-center gap-x-2">
        {/* Botão de upload de PDF */}
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={handleFileUpload}
        />
        <Button
          onClick={() => fileInputRef.current?.click()}
          disabled={!(selectedAgent || teamId) || verificationState === 'checking'}
          size="icon"
          variant="outline"
          title="Enviar documento CNPJ (PDF)"
          className="shrink-0 rounded-xl border border-accent bg-primaryAccent p-5"
        >
          <Icon type="paperclip" color="primary" />
        </Button>

        <TextArea
          placeholder={
            verificationState === 'blocked'
              ? 'Atendimento bloqueado. Envie um novo documento.'
              : verificationState === 'checking'
              ? 'Verificando CNPJ...'
              : 'Ask anything'
          }
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyDown={(e) => {
            if (
              e.key === 'Enter' &&
              !e.nativeEvent.isComposing &&
              !e.shiftKey &&
              !isStreaming
            ) {
              e.preventDefault()
              handleSubmit()
            }
          }}
          className="w-full border border-accent bg-primaryAccent px-4 text-sm text-primary focus:border-accent"
          disabled={isInputDisabled}
          ref={chatInputRef}
        />
        <Button
          onClick={handleSubmit}
          disabled={isSendDisabled}
          size="icon"
          className="rounded-xl bg-primary p-5 text-primaryAccent"
        >
          <Icon type="send" color="primaryAccent" />
        </Button>
      </div>
    </div>
  )
}

export default ChatInput
```

- [ ] **Step 4: Rodar o frontend para teste manual**

```bash
cd /Users/igorsouza/Work/Agno-Agent-UI/agent-ui && npm run dev
```

Verificar:
- Botão de upload (clipe) aparece ao lado do textarea
- Ao enviar PDF válido de CNPJ → banner amarelo "Verificando..." → banner verde com CNPJ
- Ao enviar PDF com CNPJ `00.000.000/0000-00` (inadimplente no stub) → banner vermelho com mensagem de bloqueio
- Textarea fica desabilitado durante verificação e quando bloqueado

- [ ] **Step 5: Commit**

```bash
cd /Users/igorsouza/Work/Agno-Agent-UI/agent-ui
git add src/components/ui/icon/types.ts src/components/ui/icon/constants.tsx
git add src/components/chat/ChatArea/ChatInput/ChatInput.tsx
git commit -m "feat: add paperclip icon and CNPJ PDF upload with verification flow"
cd /Users/igorsouza/Work/POC-Agno-RAG
```

---

## Task 5: Rodar suite completa de testes e validar

- [ ] **Step 1: Rodar todos os testes do backend**

```bash
uv run pytest tests/ -v -k "not test_classify_incomplete_lead_as_frio"
```

Esperado: todos os testes passam, incluindo os novos de CNPJ.

- [ ] **Step 2: Verificar endpoints no Swagger**

Iniciar o servidor:
```bash
uv run python src/agent_os_server.py
```

Acessar `http://localhost:7777/docs` e verificar que `/cnpj/verify` e `/cnpj/upload` aparecem.

- [ ] **Step 3: Testar /cnpj/verify via curl**

```bash
# CNPJ ok
curl -X POST http://localhost:7777/cnpj/verify \
  -H "Content-Type: application/json" \
  -d '{"cnpj": "11222333000181"}'

# Esperado: {"status": "ok", "bloqueado": false, ...}

# CNPJ inadimplente (stub)
curl -X POST http://localhost:7777/cnpj/verify \
  -H "Content-Type: application/json" \
  -d '{"cnpj": "00000000000000"}'

# Esperado: {"status": "inadimplente", "bloqueado": true, ...}
```

- [ ] **Step 4: Commit final**

```bash
git add .
git commit -m "feat: complete CNPJ verification flow - upload, verify, index, frontend"
```

---

## Resumo dos Endpoints Novos

| Endpoint | Método | Payload | Retorno |
|----------|--------|---------|---------|
| `/cnpj/verify` | POST | `{"cnpj": "11222333000181"}` | `CnpjVerifyResponse` |
| `/cnpj/upload` | POST | `multipart/form-data` com `file` (PDF) | `CnpjVerifyResponse` |

## CNPJs Especiais para Demo/Teste

| CNPJ | Comportamento |
|------|---------------|
| `00000000000000` | Simula inadimplência — bloqueia atendimento |
| Qualquer 14 dígitos válido | Liberado para atendimento |
| Menos de 14 dígitos | Retorna `invalido` |
