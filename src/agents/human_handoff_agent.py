"""Agente de Transbordo Humanizado."""
from agno.agent import Agent
from src.config import get_model

HANDOFF_TRIGGERS = [
    "falar com humano",
    "falar com um humano",
    "falar com pessoa",
    "falar com atendente",
    "falar com um atendente",
    "falar com vendedor",
    "falar com gerente",
    "falar com o gerente",
    "atendimento humano",
    "quero humano",
    "preciso de humano",
    "me passa para",
    "me passar para",
    "transferir para",
    "pessoa real",
    "não quero robô",
    "não quero bot",
    "fala com alguém",
    "atendente",
    "gerente",
]

HUMAN_HANDOFF_INSTRUCTIONS = """
Você é o Agente de Transbordo da Aço Cearense, distribuidora de produtos de aço do Nordeste com sede em Fortaleza — CE.

Sua única função é informar ao cliente, de forma empática e profissional,
que ele será transferido para um consultor humano da Aço Cearense.

Gere sempre uma mensagem que:
1. Agradeça pela paciência em nome da Aço Cearense
2. Confirme a transferência para um consultor especializado da Aço Cearense
3. Informe prazo de retorno (até 30 minutos em horário comercial: seg-sex 7h–18h, sáb 7h–12h)
4. Deixe o cliente confortável para aguardar

Seja cordial, breve e tranquilizador. Mencione a Aço Cearense pelo nome.
"""


def detect_handoff_trigger(message: str) -> dict:
    """
    Detecta se a mensagem contém pedido de atendimento humano.
    Verificação por palavras-chave (sem chamada à IA).

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
    """Cria o agente de transbordo humanizado."""
    return Agent(
        name="Agente de Transbordo",
        model=get_model(),
        instructions=HUMAN_HANDOFF_INSTRUCTIONS,
        markdown=True,
    )
