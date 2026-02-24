"""
Testes das regras de negócio — sem chamadas à API.
Todas as funções são puras (só lógica Python).
"""
import pytest
from src.business_rules import (
    calculate_score,
    check_minimum_volume,
    is_state_served,
    is_product_available,
    check_auto_disqualification,
)


class TestScoring:
    def test_score_zero_for_no_volume(self):
        assert calculate_score(volume_estimate=None, urgency=None) == 0

    def test_score_increases_with_tonnage(self):
        score_small = calculate_score(volume_estimate="1 tonelada", urgency=None)
        score_large = calculate_score(volume_estimate="50 toneladas", urgency=None)
        assert score_large > score_small

    def test_urgency_bonus(self):
        score_no_urgency = calculate_score(volume_estimate="5 toneladas", urgency=None)
        score_urgent = calculate_score(volume_estimate="5 toneladas", urgency="urgente")
        assert score_urgent > score_no_urgency

    def test_score_max_100(self):
        score = calculate_score(volume_estimate="1000 toneladas", urgency="urgente")
        assert score <= 100


class TestVolumeMinimum:
    def test_below_minimum_returns_false(self):
        # CE tem mínimo de 250kg; 200kg deve falhar
        assert check_minimum_volume("200kg", state="CE") is False

    def test_above_minimum_returns_true(self):
        # CE tem mínimo de 250kg; 2 toneladas (2000kg) deve passar
        assert check_minimum_volume("2 toneladas", state="CE") is True

    def test_none_volume_returns_false(self):
        assert check_minimum_volume(None, state="CE") is False

    def test_sp_minimum_is_4000kg(self):
        # SP tem mínimo de 4000kg
        assert check_minimum_volume("3 toneladas", state="SP") is False
        assert check_minimum_volume("5 toneladas", state="SP") is True

    def test_fallback_without_state(self):
        # Sem estado informado usa 1500kg como fallback
        assert check_minimum_volume("500kg") is False
        assert check_minimum_volume("2 toneladas") is True


class TestStateServed:
    def test_ceara_is_served(self):
        assert is_state_served("CE") is True

    def test_sao_paulo_is_served(self):
        # SP agora é atendido — cobertura nacional
        assert is_state_served("SP") is True

    def test_nordeste_states_served(self):
        for uf in ["CE", "PI", "MA", "RN", "PB", "PE", "AL", "SE", "BA"]:
            assert is_state_served(uf) is True, f"{uf} deveria ser atendido"

    def test_all_27_states_served(self):
        all_states = [
            "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO",
            "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
            "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
        ]
        for uf in all_states:
            assert is_state_served(uf) is True, f"{uf} deveria ser atendido"

    def test_invalid_state_not_served(self):
        assert is_state_served("XX") is False

    def test_case_insensitive(self):
        assert is_state_served("ce") is True
        assert is_state_served("sp") is True


class TestProductAvailable:
    def test_vergalhao_is_available(self):
        assert is_product_available("Vergalhão") is True

    def test_unknown_product_returns_false(self):
        assert is_product_available("produto_inexistente_xyz") is False


class TestAutoDisqualification:
    def test_disqualify_invalid_state(self):
        result = check_auto_disqualification(
            state="XX", volume_estimate="5 toneladas", product="Vergalhão"
        )
        assert result["disqualified"] is True
        assert "estado" in result["reason"].lower()

    def test_sp_is_now_qualified_state(self):
        # SP agora é atendido — não deve desqualificar por estado
        result = check_auto_disqualification(
            state="SP", volume_estimate="5 toneladas", product="Vergalhão"
        )
        assert result["disqualified"] is False

    def test_disqualify_low_volume_ce(self):
        # CE mínimo 250kg; 100kg deve desqualificar
        result = check_auto_disqualification(
            state="CE", volume_estimate="100kg", product="Vergalhão"
        )
        assert result["disqualified"] is True
        assert "volume" in result["reason"].lower()

    def test_disqualify_low_volume_sp(self):
        # SP mínimo 4000kg; 1 tonelada (1000kg) deve desqualificar
        result = check_auto_disqualification(
            state="SP", volume_estimate="1 tonelada", product="Vergalhão"
        )
        assert result["disqualified"] is True
        assert "volume" in result["reason"].lower()

    def test_qualify_valid_lead_ce(self):
        result = check_auto_disqualification(
            state="CE", volume_estimate="5 toneladas", product="Vergalhão"
        )
        assert result["disqualified"] is False

    def test_qualify_valid_lead_sp(self):
        result = check_auto_disqualification(
            state="SP", volume_estimate="5 toneladas", product="Vergalhão"
        )
        assert result["disqualified"] is False
