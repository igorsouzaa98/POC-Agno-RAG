"""
Regras de negócio da Aço Cearense.
Todas as funções são puras (sem side effects) para facilitar testes.
"""
import re
from typing import Optional

# Estados atendidos
STATES_SERVED = {"CE", "PI", "MA", "RN", "PB", "PE", "AL", "SE", "BA"}

# Volume mínimo em kg
MINIMUM_VOLUME_KG = 1500

# Produtos disponíveis (normalizado em lowercase)
AVAILABLE_PRODUCTS = {
    "vergalhão", "vergalhao", "arame recozido", "tubo industrial",
    "tubo quadrado", "tubo retangular", "tubo redondo",
    "telha trapezoidal galvanizada", "chapa galvanizada",
    "barra chata", "cantoneira", "perfil u",
    "metalon", "ferro",
}


def _parse_volume_to_kg(volume_str: Optional[str]) -> float:
    """Converte string de volume para kg. Ex: "5 toneladas" → 5000.0"""
    if not volume_str:
        return 0.0
    text = volume_str.lower().strip()
    numbers = re.findall(r"[\d.,]+", text)
    if not numbers:
        return 0.0
    try:
        amount = float(numbers[0].replace(",", "."))
    except ValueError:
        return 0.0
    if "ton" in text or text.endswith("t") or " t " in text:
        return amount * 1000
    elif "unidade" in text or " un" in text or "pç" in text or "peça" in text:
        return amount * 20
    else:
        return amount  # assume kg


def calculate_score(volume_estimate: Optional[str], urgency: Optional[str]) -> int:
    """Score de 0-100. Volume: até 70 pts. Urgência: +30 pts."""
    score = 0
    volume_kg = _parse_volume_to_kg(volume_estimate)
    if volume_kg > 0:
        score += min(70, int(volume_kg / 100))
    if urgency and any(w in urgency.lower() for w in ["urgente", "imediato", "hoje", "amanhã", "semana"]):
        score += 30
    return min(100, score)


def check_minimum_volume(volume_estimate: Optional[str], state: Optional[str] = None) -> bool:
    """Retorna True se volume >= 1500kg."""
    return _parse_volume_to_kg(volume_estimate) >= MINIMUM_VOLUME_KG


def is_state_served(state: Optional[str]) -> bool:
    """Retorna True se estado está no Nordeste atendido."""
    if not state:
        return False
    return state.upper().strip() in STATES_SERVED


def is_product_available(product: Optional[str]) -> bool:
    """Retorna True se produto está no portfólio."""
    if not product:
        return False
    product_lower = product.lower().strip()
    return any(p in product_lower or product_lower in p for p in AVAILABLE_PRODUCTS)


def check_auto_disqualification(
    state: Optional[str],
    volume_estimate: Optional[str],
    product: Optional[str],
) -> dict:
    """
    Aplica regras de desqualificação. Retorna {"disqualified": bool, "reason": str}.
    Ordem: 1. Estado fora da área 2. Volume mínimo 3. Produto indisponível
    """
    if state and not is_state_served(state):
        return {
            "disqualified": True,
            "reason": f"Infelizmente não atendemos o estado {state.upper()}. Operamos no Nordeste (CE, PI, MA, RN, PB, PE, AL, SE, BA).",
        }
    if volume_estimate and not check_minimum_volume(volume_estimate, state):
        return {
            "disqualified": True,
            "reason": f"O volume informado ({volume_estimate}) está abaixo do mínimo de 1.500kg por pedido para a sua região.",
        }
    if product and not is_product_available(product):
        return {
            "disqualified": True,
            "reason": f"O produto '{product}' não está disponível no nosso portfólio. Trabalhamos com vergalhões, tubos, chapas, telhas e perfis estruturais.",
        }
    return {"disqualified": False, "reason": ""}
