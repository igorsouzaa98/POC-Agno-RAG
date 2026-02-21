"""
Sistema de Follow-up Cadenciado Pós-Orçamento.

Após envio de orçamento, agenda mensagens automáticas em:
  - 2h, 10h, 20h, 48h

Se cliente responder: chamar cancel() para cancelar os follow-ups pendentes.
Se nenhuma resposta em 48h: ticket encerrado por inatividade.

Uso em produção:
    manager = FollowUpManager()
    manager.register(session_id="sess-001", lead_name="Carlos", contact="11999998888")
    # Quando cliente responder:
    manager.cancel("sess-001")

Em testes, use dry_run=True para não inicializar o APScheduler.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# Intervalos em horas
FOLLOWUP_INTERVALS_HOURS = [2, 10, 20, 48]

# Mensagens por tentativa (1-indexed)
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
    contact: str
    attempt: int = 0
    max_attempts: int = 4
    completed: bool = False
    registered_at: datetime = field(default_factory=datetime.now)
    last_attempt_at: Optional[datetime] = None


class FollowUpManager:
    """
    Gerenciador de follow-ups cadenciados.

    Args:
        dry_run: Se True, não inicializa APScheduler (para testes).
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
        Registra lead para follow-ups automáticos.
        Agenda mensagens em 2h, 10h, 20h e 48h.
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
        """
        if session_id in self._states:
            self._states[session_id].completed = True

        if not self._dry_run and hasattr(self, "_scheduler"):
            for i in range(1, 5):
                job_id = f"{session_id}_attempt_{i}"
                try:
                    self._scheduler.remove_job(job_id)
                except Exception:
                    pass

    def has_pending(self, session_id: str) -> bool:
        """Retorna True se há follow-up registrado e não concluído."""
        state = self._states.get(session_id)
        return state is not None and not state.completed

    def _build_message(self, lead_name: str, attempt: int) -> str:
        """Constrói mensagem personalizada para a tentativa N (1-4)."""
        template = FOLLOWUP_MESSAGES.get(attempt, FOLLOWUP_MESSAGES[4])
        return template.format(name=lead_name)

    def _execute_followup(self, session_id: str, attempt: int):
        """
        Executa o follow-up (chamado pelo scheduler).
        Stub: em produção, chamar API do Blip/WhatsApp aqui.
        """
        state = self._states.get(session_id)
        if not state or state.completed:
            return

        message = self._build_message(state.lead_name, attempt)
        state.attempt = attempt
        state.last_attempt_at = datetime.now()

        print(f"[FOLLOW-UP] session={session_id} attempt={attempt}/{state.max_attempts}")
        print(f"[FOLLOW-UP] contact={state.contact}")
        print(f"[FOLLOW-UP] message={message}")

        if attempt >= state.max_attempts:
            state.completed = True
            print(f"[FOLLOW-UP] Ticket {session_id} encerrado por inatividade.")
