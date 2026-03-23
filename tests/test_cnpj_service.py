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
    assert service.validate_cnpj("11.222.333/0001-81") is True


def test_check_inadimplencia_cnpj_limpo(service):
    result = service.check_inadimplencia("11222333000181")
    assert "inadimplente" in result
    assert isinstance(result["inadimplente"], bool)


def test_check_inadimplencia_stub_retorna_false_por_padrao(service):
    result = service.check_inadimplencia("11222333000181")
    assert result["inadimplente"] is False


def test_check_inadimplencia_cnpj_bloqueado(service):
    result = service.check_inadimplencia("00000000000000")
    assert result["inadimplente"] is True


def test_check_active_session_cnpj_sem_sessao(service):
    result = service.check_active_session("99999999999999")
    assert result["em_atendimento"] is False
    assert result["session_id"] is None


def test_check_active_session_cnpj_em_atendimento_stub(service):
    result = service.check_active_session("11111111000191")
    assert result["em_atendimento"] is True
    assert result["session_id"] is not None


def test_extract_cnpj_from_text(service):
    text = "CNPJ: 11.222.333/0001-81 - Empresa Teste LTDA"
    cnpj = service.extract_cnpj_from_text(text)
    assert cnpj == "11222333000181"


def test_extract_cnpj_from_text_sem_cnpj(service):
    text = "Texto sem CNPJ nenhum aqui"
    cnpj = service.extract_cnpj_from_text(text)
    assert cnpj is None
