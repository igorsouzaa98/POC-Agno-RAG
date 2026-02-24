# src/data/weight_rules.py
"""
Regras de peso mínimo CIF por estado para a Aço Cearense.

Fonte: Planilha "Range de Aprovação - Peso Final.xlsx"
Tipo: Peso Carbono MTS | Frete: CIF
Extraído em: 2026-02-24

Estes valores são críticos para o negócio — mantidos como dict
Python (determinístico) em vez de RAG para evitar alucinações.
"""
from typing import Optional

PESO_MINIMO_CIF_POR_ESTADO: dict[str, int] = {
    # Nordeste — sede da Aço Cearense em Fortaleza/CE
    "CE": 250,
    "AL": 1500,
    "MA": 1500,
    "PB": 1500,
    "PI": 1500,
    "SE": 1500,
    "BA": 1500,
    "PE": 1500,
    "RN": 1500,
    # Norte
    "PA": 1500,
    "AC": 10000,
    "AM": 10000,
    "AP": 8000,
    "RO": 10000,
    "RR": 10000,
    # Centro-Oeste / Sudeste
    "GO": 4000,
    "DF": 4000,
    "MG": 4000,
    "SP": 4000,
    "RJ": 4000,
    "ES": 4000,
    "MT": 4000,
    "MS": 4000,
    "TO": 4000,
    # Sul
    "PR": 4000,
    "RS": 8000,
    "SC": 8000,
}


def get_peso_minimo(uf: str) -> Optional[int]:
    """Retorna o peso mínimo CIF em kg para o estado informado, ou None se não encontrado."""
    return PESO_MINIMO_CIF_POR_ESTADO.get(uf.upper())
