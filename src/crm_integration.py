"""
Integração CRM — Stub para Salesforce.

Este módulo é um STUB (simulação) da integração com o Salesforce.
Em produção, substitua os métodos _stub_* por chamadas reais usando
a biblioteca `simple-salesforce`:

    pip install simple-salesforce

    from simple_salesforce import Salesforce
    sf = Salesforce(
        username=os.getenv("SF_USERNAME"),
        password=os.getenv("SF_PASSWORD"),
        security_token=os.getenv("SF_SECURITY_TOKEN"),
    )
    sf.Lead.update(lead_id, {"Status": status.value, "Lead_Score__c": score})

Campos do Salesforce que serão atualizados:
    - Lead.Status → FRIO, MORNO, QUENTE, DESQUALIFICADO
    - Lead.Lead_Score__c → score numérico (0-100)
    - Lead.Disqualification_Reason__c → motivo da desqualificação
"""
import uuid
import logging
from enum import Enum
from typing import Optional

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
        stub_mode: Se True, simula chamadas sem fazer requests reais.
                   Use True em desenvolvimento e testes.
    """

    def __init__(self, stub_mode: bool = True):
        self._stub_mode = stub_mode
        if not stub_mode:
            self._init_salesforce()

    def _init_salesforce(self):
        """Inicializa conexão real com Salesforce. TODO: implementar."""
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
            disqualification_reason: Motivo (se desqualificado)

        Returns:
            dict: {"success": bool, "lead_id": str}
        """
        if self._stub_mode:
            logger.info(
                f"[CRM STUB] update_lead: id={lead_id} status={status.value} score={score}"
            )
            if disqualification_reason:
                logger.info(f"[CRM STUB] reason={disqualification_reason}")
            return {"success": True, "lead_id": lead_id}
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
            fake_id = f"STUB-{str(uuid.uuid4())[:8].upper()}"
            logger.info(f"[CRM STUB] create_lead: name={name} email={email} id={fake_id}")
            return {"success": True, "id": fake_id}
        raise NotImplementedError("Modo produção não implementado")
