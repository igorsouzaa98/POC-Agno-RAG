from fastapi import FastAPI, HTTPException
from src.models import IncomingMessage, AgentResponse, LeadClassification, LeadData
from src.orchestrator import create_steel_sales_team

app = FastAPI(
    title="POC Agno - Agentes de Vendas de Aço",
    description="API de automação do fluxo de atendimento para distribuidora de aço",
    version="0.1.0",
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
        team = get_team()

        context = message.message
        if message.lead_data:
            context = f"[DADOS DO LEAD: {message.lead_data.model_dump_json()}]\n\nMensagem do cliente: {message.message}"

        response = team.run(context)
        content = response.content if hasattr(response, 'content') else str(response)
        classification = extract_classification(content)

        lead_data = message.lead_data or LeadData(session_id=message.session_id)
        lead_data.classification = classification

        return AgentResponse(
            session_id=message.session_id,
            message=content,
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
