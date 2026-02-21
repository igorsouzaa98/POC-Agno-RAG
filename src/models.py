from enum import Enum
from pydantic import BaseModel
from typing import Optional


class LeadClassification(str, Enum):
    FRIO = "FRIO"
    MORNO = "MORNO"
    QUENTE = "QUENTE"


class ProductCategory(str, Enum):
    CONSTRUCAO_CIVIL = "construcao_civil"
    ESTRUTURAL_SERRALHERIA = "estrutural_serralheria"
    PLANOS = "planos"
    TUBOS = "tubos"


class ClientType(str, Enum):
    CONSTRUTORA = "Construtora"
    SERRALHERIA = "Serralheria"
    REVENDA = "Revenda"
    OUTRO = "Outro"


class LeadData(BaseModel):
    session_id: str
    name: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    cnpj: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    client_type: Optional[ClientType] = None
    product_interest: Optional[str] = None
    technical_product: Optional[str] = None
    volume_estimate: Optional[str] = None
    urgency: Optional[str] = None
    classification: LeadClassification = LeadClassification.FRIO
    missing_fields: list[str] = []
    score: int = 0
    disqualified_reason: Optional[str] = None


class IncomingMessage(BaseModel):
    session_id: str
    message: str
    lead_data: Optional[LeadData] = None


class AgentResponse(BaseModel):
    session_id: str
    message: str
    classification: LeadClassification
    lead_data: LeadData
    next_action: str
