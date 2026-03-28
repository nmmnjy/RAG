import pytest

from app.core.errors import AppError
from app.schemas.document_parse import DocumentStatus
from app.services.parse_task_state_machine import ParseTaskStateMachine


def test_valid_transition() -> None:
    machine = ParseTaskStateMachine()
    assert machine.can_transition(DocumentStatus.pending, DocumentStatus.parsing)


def test_invalid_transition() -> None:
    machine = ParseTaskStateMachine()
    with pytest.raises(AppError):
        machine.assert_transition(DocumentStatus.pending, DocumentStatus.succeeded)
