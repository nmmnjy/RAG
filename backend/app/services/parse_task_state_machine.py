from app.core.errors import AppError, ERROR_CODE
from app.schemas.document_parse import DocumentStatus


class ParseTaskStateMachine:
    _transitions: dict[DocumentStatus, set[DocumentStatus]] = {
        DocumentStatus.pending: {DocumentStatus.parsing},
        DocumentStatus.parsing: {
            DocumentStatus.succeeded,
            DocumentStatus.failed,
            DocumentStatus.retryable,
        },
        DocumentStatus.retryable: {DocumentStatus.parsing, DocumentStatus.failed},
        DocumentStatus.failed: {DocumentStatus.retryable},
        DocumentStatus.succeeded: set(),
    }

    def can_transition(self, from_status: DocumentStatus, to_status: DocumentStatus) -> bool:
        return to_status in self._transitions[from_status]

    def assert_transition(self, from_status: DocumentStatus, to_status: DocumentStatus) -> None:
        if not self.can_transition(from_status, to_status):
            raise AppError(
                code=ERROR_CODE.COMMON_CONFLICT,
                message=f"invalid status transition: {from_status} -> {to_status}",
                status_code=409,
            )


state_machine = ParseTaskStateMachine()
