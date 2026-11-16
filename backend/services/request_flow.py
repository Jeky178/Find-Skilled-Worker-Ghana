"""
Who may move a service request to which status.

  pending ──artisan──> accepted ──artisan──> in_progress ──artisan or customer──> completed
     │ └──artisan──> rejected        │                 └──artisan──> cancelled
     └──customer──> cancelled        └──customer or artisan──> cancelled
"""
from models import RequestStatus as S

TRANSITIONS: dict[str, dict[S, set[S]]] = {
    "artisan": {
        S.pending: {S.accepted, S.rejected},
        S.accepted: {S.in_progress, S.cancelled},
        S.in_progress: {S.completed, S.cancelled},
    },
    "customer": {
        S.pending: {S.cancelled},
        S.accepted: {S.cancelled},
        S.in_progress: {S.completed},
    },
}

NOTE_REQUIRED = {("artisan", S.rejected), ("artisan", S.cancelled)}
OPEN_STATUSES = (S.pending, S.accepted, S.in_progress)
CONTACT_VISIBLE = (S.accepted, S.in_progress, S.completed)


def allowed_actions(role: str, status: S) -> list[str]:
    return sorted(s.value for s in TRANSITIONS.get(role, {}).get(status, set()))


def can_move(role: str, current: S, target: S) -> bool:
    return target in TRANSITIONS.get(role, {}).get(current, set())
