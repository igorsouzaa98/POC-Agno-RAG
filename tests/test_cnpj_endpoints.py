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
