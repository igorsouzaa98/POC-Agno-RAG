import pytest
from src.crm_integration import CRMClient, LeadStatus


class TestCRMClient:
    def test_stub_mode_does_not_raise(self):
        client = CRMClient(stub_mode=True)
        client.update_lead_status(lead_id="LEAD-001", status=LeadStatus.MORNO, score=75)

    def test_stub_mode_returns_success(self):
        client = CRMClient(stub_mode=True)
        result = client.update_lead_status(
            lead_id="LEAD-001", status=LeadStatus.QUENTE, score=90
        )
        assert result["success"] is True

    def test_stub_mode_create_lead(self):
        client = CRMClient(stub_mode=True)
        result = client.create_lead(
            name="Carlos", email="c@test.com", phone="11999998888", cnpj="12345678000100"
        )
        assert result["success"] is True
        assert "id" in result

    def test_lead_status_values(self):
        assert LeadStatus.FRIO == "FRIO"
        assert LeadStatus.MORNO == "MORNO"
        assert LeadStatus.QUENTE == "QUENTE"
        assert LeadStatus.DESQUALIFICADO == "DESQUALIFICADO"

    def test_create_lead_generates_unique_ids(self):
        client = CRMClient(stub_mode=True)
        r1 = client.create_lead(name="A", email="a@a.com", phone="11999990001")
        r2 = client.create_lead(name="B", email="b@b.com", phone="11999990002")
        assert r1["id"] != r2["id"]
