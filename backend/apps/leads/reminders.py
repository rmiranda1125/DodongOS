"""
Deterministic, read-only CRM reminder services.

These functions never mutate CRM data. They exist so background
automation (Phase 6) can detect actionable CRM conditions through
a stable service boundary instead of touching the ORM from
orchestration code.

"Last meaningful activity" for a lead is defined here as the most
recent of:

- the newest ``LeadActivity.created_at`` for that lead
  (notes, calls, emails, meetings, follow-ups, and status changes
  are all persisted as ``LeadActivity`` rows by the CRM services),
- the lead's own ``created_at`` (used as the baseline when a lead
  has no recorded activity yet).

``Lead.updated_at`` is intentionally NOT used: it is ``auto_now``
and is rewritten by unrelated field updates (AI re-scoring, etc.),
so it is not a reliable signal of human engagement.
"""

from datetime import timedelta

from django.db.models import Max
from django.utils import timezone

from .models import Lead, LeadTask


ACTIONABLE_TASK_STATUSES = (
    "pending",
    "in_progress",
)

INACTIVE_LEAD_STATUSES = (
    "won",
    "lost",
)


def _require_positive_number(*, name, value):
    if isinstance(value, bool) or not isinstance(
        value,
        (int, float),
    ):
        raise ValueError(
            f"{name} must be a positive number.",
        )

    if value <= 0:
        raise ValueError(
            f"{name} must be a positive number.",
        )


def get_due_soon_tasks(
    *,
    within_hours,
    now=None,
):
    """
    Return actionable CRM tasks whose due date falls after ``now``
    and within the next ``within_hours`` hours.

    - only ``pending`` / ``in_progress`` tasks
    - ``due_date`` must be set
    - already-overdue tasks are excluded (``due_date`` > ``now``)
    - the horizon boundary is inclusive (``due_date`` <= horizon)
    - deterministic ordering: ``due_date`` then ``id``
    """

    _require_positive_number(
        name="within_hours",
        value=within_hours,
    )

    if now is None:
        now = timezone.now()

    horizon = now + timedelta(
        hours=within_hours,
    )

    tasks = LeadTask.objects.filter(
        status__in=ACTIONABLE_TASK_STATUSES,
        due_date__isnull=False,
        due_date__gt=now,
        due_date__lte=horizon,
    ).order_by(
        "due_date",
        "id",
    )

    return list(tasks)


def get_stale_leads(
    *,
    stale_after_days,
    now=None,
):
    """
    Return active CRM leads with no meaningful activity within the
    last ``stale_after_days`` days.

    - ``won`` / ``lost`` leads are excluded
    - a lead is stale when its last meaningful activity timestamp
      is at or before ``now - stale_after_days`` (boundary
      inclusive)
    - deterministic ordering: oldest last-activity first, then
      ``id``

    Each returned lead carries a transient
    ``last_meaningful_activity_at`` attribute (not persisted) so
    callers can serialize it without re-querying.
    """

    _require_positive_number(
        name="stale_after_days",
        value=stale_after_days,
    )

    if now is None:
        now = timezone.now()

    cutoff = now - timedelta(
        days=stale_after_days,
    )

    leads = (
        Lead.objects.exclude(
            status__in=INACTIVE_LEAD_STATUSES,
        )
        .annotate(
            latest_activity_at=Max(
                "activities__created_at",
            ),
        )
    )

    stale = []

    for lead in leads:
        last_meaningful = lead.created_at

        if (
            lead.latest_activity_at is not None
            and lead.latest_activity_at > last_meaningful
        ):
            last_meaningful = lead.latest_activity_at

        if last_meaningful <= cutoff:
            lead.last_meaningful_activity_at = last_meaningful
            stale.append(lead)

    stale.sort(
        key=lambda lead: (
            lead.last_meaningful_activity_at,
            lead.id,
        ),
    )

    return stale
