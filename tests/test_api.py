import pytest
from fastapi.testclient import TestClient
from src.api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_out_of_state_lead_gets_disqualified():
    from fastapi.testclient import TestClient
    from src.api import app
    from src.models import IncomingMessage, LeadData

    client = TestClient(app)
    lead = LeadData(session_id="test-sp", state="SP", volume_estimate="5 toneladas")
    msg = IncomingMessage(session_id="test-sp", message="Quero vergalhão", lead_data=lead)
    response = client.post("/chat", json=msg.model_dump())
    assert response.status_code == 200
    data = response.json()
    assert data["lead_data"]["disqualified_reason"] is not None
    assert data["next_action"] == "disqualified"


def test_score_calculated_from_volume():
    from fastapi.testclient import TestClient
    from src.api import app
    from src.models import IncomingMessage, LeadData

    client = TestClient(app)
    # Lead com volume alto, CE (não desqualificado por estado)
    # Mas sem volume mínimo suficiente para desqualificar
    lead = LeadData(session_id="test-score", state="CE", volume_estimate="20 toneladas")
    msg = IncomingMessage(session_id="test-score", message="Quero vergalhão", lead_data=lead)
    response = client.post("/chat", json=msg.model_dump())
    assert response.status_code == 200
    data = response.json()
    assert data["lead_data"]["score"] > 0


def test_low_volume_lead_gets_disqualified():
    from fastapi.testclient import TestClient
    from src.api import app
    from src.models import IncomingMessage, LeadData

    client = TestClient(app)
    lead = LeadData(session_id="test-vol", state="CE", volume_estimate="100kg")
    msg = IncomingMessage(session_id="test-vol", message="Quero vergalhão", lead_data=lead)
    response = client.post("/chat", json=msg.model_dump())
    assert response.status_code == 200
    data = response.json()
    assert data["next_action"] == "disqualified"
    assert data["lead_data"]["disqualified_reason"] is not None
