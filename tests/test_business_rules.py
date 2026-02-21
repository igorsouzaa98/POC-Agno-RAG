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
        assert check_minimum_volume("500kg", state="CE") is False

    def test_above_minimum_returns_true(self):
        assert check_minimum_volume("2 toneladas", state="CE") is True

    def test_none_volume_returns_false(self):
        assert check_minimum_volume(None, state="CE") is False


class TestStateServed:
    def test_ceara_is_served(self):
        assert is_state_served("CE") is True

    def test_sao_paulo_is_not_served(self):
        assert is_state_served("SP") is False

    def test_case_insensitive(self):
        assert is_state_served("ce") is True


class TestProductAvailable:
    def test_vergalhao_is_available(self):
        assert is_product_available("Vergalhão") is True

    def test_unknown_product_returns_false(self):
        assert is_product_available("produto_inexistente_xyz") is False


class TestAutoDisqualification:
    def test_disqualify_out_of_state(self):
        result = check_auto_disqualification(
            state="SP", volume_estimate="5 toneladas", product="Vergalhão"
        )
        assert result["disqualified"] is True
        assert "estado" in result["reason"].lower()

    def test_disqualify_low_volume(self):
        result = check_auto_disqualification(
            state="CE", volume_estimate="100kg", product="Vergalhão"
        )
        assert result["disqualified"] is True
        assert "volume" in result["reason"].lower()

    def test_qualify_valid_lead(self):
        result = check_auto_disqualification(
            state="CE", volume_estimate="5 toneladas", product="Vergalhão"
        )
        assert result["disqualified"] is False
