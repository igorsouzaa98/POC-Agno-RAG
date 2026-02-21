import pytest
from src.agents.human_handoff_agent import (
    create_human_handoff_agent,
    detect_handoff_trigger,
    HANDOFF_TRIGGERS,
)


class TestHandoffDetection:
    def test_detect_explicit_human_request(self):
        result = detect_handoff_trigger("quero falar com um humano")
        assert result["should_handoff"] is True
        assert result["reason"] == "explicit_request"

    def test_detect_atendente_request(self):
        result = detect_handoff_trigger("pode me passar para um atendente?")
        assert result["should_handoff"] is True

    def test_detect_gerente_request(self):
        result = detect_handoff_trigger("preciso falar com o gerente")
        assert result["should_handoff"] is True

    def test_normal_message_no_handoff(self):
        result = detect_handoff_trigger("quero 5 toneladas de vergalhão")
        assert result["should_handoff"] is False

    def test_agent_created(self):
        agent = create_human_handoff_agent()
        assert agent is not None
        assert agent.name == "Agente de Transbordo"

    def test_handoff_triggers_list_not_empty(self):
        assert len(HANDOFF_TRIGGERS) > 0
