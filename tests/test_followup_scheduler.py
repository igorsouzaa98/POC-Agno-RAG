"""
Testes do sistema de follow-up cadenciado.
Testa a lógica de estado sem inicializar o scheduler real.
"""
import pytest
from src.followup_scheduler import (
    FollowUpState,
    FollowUpManager,
    FOLLOWUP_INTERVALS_HOURS,
)


class TestFollowUpIntervals:
    def test_correct_intervals(self):
        assert FOLLOWUP_INTERVALS_HOURS == [2, 10, 20, 48]


class TestFollowUpState:
    def test_initial_state(self):
        state = FollowUpState(session_id="test-001", lead_name="João", contact="11999998888")
        assert state.attempt == 0
        assert state.completed is False
        assert state.session_id == "test-001"

    def test_max_attempts_is_four(self):
        state = FollowUpState(session_id="test-001", lead_name="João", contact="11999998888")
        assert state.max_attempts == 4


class TestFollowUpManager:
    def test_register_lead_for_followup(self):
        manager = FollowUpManager(dry_run=True)
        manager.register(session_id="sess-001", lead_name="Carlos", contact="11999998888")
        assert manager.has_pending("sess-001") is True

    def test_cancel_followup(self):
        manager = FollowUpManager(dry_run=True)
        manager.register(session_id="sess-001", lead_name="Carlos", contact="11999998888")
        manager.cancel("sess-001")
        assert manager.has_pending("sess-001") is False

    def test_get_followup_message_first(self):
        manager = FollowUpManager(dry_run=True)
        msg = manager._build_message(lead_name="Carlos", attempt=1)
        assert "Carlos" in msg
        assert len(msg) > 20

    def test_get_followup_message_last(self):
        manager = FollowUpManager(dry_run=True)
        msg = manager._build_message(lead_name="Carlos", attempt=4)
        assert "Carlos" in msg

    def test_unregistered_session_not_pending(self):
        manager = FollowUpManager(dry_run=True)
        assert manager.has_pending("session-inexistente") is False
