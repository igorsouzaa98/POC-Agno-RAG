from src.data.weight_rules import PESO_MINIMO_CIF_POR_ESTADO, get_peso_minimo


def test_ce_tem_menor_minimo():
    assert PESO_MINIMO_CIF_POR_ESTADO["CE"] == 250


def test_nordeste_tem_1500():
    for uf in ["AL", "MA", "PB", "PI", "SE", "BA", "PE", "RN"]:
        assert PESO_MINIMO_CIF_POR_ESTADO[uf] == 1500, f"{uf} deveria ser 1500"


def test_sudeste_tem_4000():
    for uf in ["SP", "MG", "RJ", "GO", "DF"]:
        assert PESO_MINIMO_CIF_POR_ESTADO[uf] == 4000, f"{uf} deveria ser 4000"


def test_get_peso_minimo_estado_valido():
    assert get_peso_minimo("CE") == 250
    assert get_peso_minimo("SP") == 4000


def test_get_peso_minimo_estado_invalido_retorna_none():
    assert get_peso_minimo("XX") is None


def test_todos_estados_cobertos():
    estados_br = [
        "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO",
        "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
        "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"
    ]
    for uf in estados_br:
        assert uf in PESO_MINIMO_CIF_POR_ESTADO, f"{uf} não encontrado no dict"
