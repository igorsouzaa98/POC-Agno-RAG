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
    ],
)

app = agent_os.get_app()

# Starlette não suporta wildcard de subdomínio (ex: *.vercel.app) em allow_origins.
# Usamos allow_origin_regex para cobrir todos os deploys do Vercel.
from starlette.middleware.cors import CORSMiddleware
app.user_middleware = [m for m in app.user_middleware if m.cls != CORSMiddleware]
app.middleware_stack = None
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

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

    verify_response = await cnpj_verify(CnpjVerifyRequest(cnpj=cnpj))

    try:
        _cnpj_service.index_cnpj_document(cnpj, file_bytes)
    except Exception:
        pass  # Indexação não deve bloquear o fluxo

    return verify_response

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
