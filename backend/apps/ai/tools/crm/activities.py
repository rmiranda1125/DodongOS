from django.conf import settings

from apps.leads import services as lead_services


def _serialize_datetime(value):
    if value is None:
        return None

    return value.isoformat()


def _serialize_activity(activity):
    """
    Convert LeadActivity into JSON-safe structured data.
    """

    return {
        "id": activity.id,
        "lead_id": activity.lead_id,
        "lead_company": activity.lead.company_name,
        "activity_type": activity.activity_type,
        "description": activity.description,
        "created_at": _serialize_datetime(
            activity.created_at,
        ),
    }


def get_lead_activities_tool(
    *,
    lead_id,
    activity_type=None,
    limit=50,
):
    """
    Read-only CRM tool.

    Return activity history for one lead through the
    CRM service layer.

    This function must never query Django models directly.
    """

    if (
        not isinstance(lead_id, int)
        or isinstance(lead_id, bool)
        or lead_id < 1
    ):
        return {
            "success": False,
            "error": {
                "code": "INVALID_LEAD_ID",
                "message": "lead_id must be a positive integer.",
            },
        }

    if not isinstance(limit, int) or isinstance(limit, bool):
        return {
            "success": False,
            "error": {
                "code": "INVALID_LIMIT",
                "message": "limit must be an integer.",
            },
        }

    if limit < 1 or limit > 100:
        return {
            "success": False,
            "error": {
                "code": "INVALID_LIMIT",
                "message": "limit must be between 1 and 100.",
            },
        }

    allowed_activity_types = {
        "note",
        "call",
        "email",
        "meeting",
        "follow_up",
        "status_changed",
    }

    if (
        activity_type is not None
        and activity_type not in allowed_activity_types
    ):
        return {
            "success": False,
            "error": {
                "code": "INVALID_ACTIVITY_TYPE",
                "message": (
                    "activity_type must be one of: "
                    "note, call, email, meeting, "
                    "follow_up, status_changed."
                ),
            },
        }

    try:
        activities = lead_services.get_lead_activities_by_id(
            lead_id=lead_id,
            activity_type=activity_type,
        )

        if activities is None:
            return {
                "success": False,
                "error": {
                    "code": "LEAD_NOT_FOUND",
                    "message": (
                        f"Lead {lead_id} was not found."
                    ),
                },
            }

        return {
            "success": True,
            "data": [
                _serialize_activity(activity)
                for activity in activities[:limit]
            ],
        }

    except Exception:
        return {
            "success": False,
            "error": {
                "code": "CRM_TOOL_ERROR",
                "message": "Unable to retrieve lead activities.",
            },
        }

def add_lead_note_tool(
    *,
    lead_id,
    activity_type,
    description,
):
    """
    Add one explicitly confirmed note to a CRM lead.

    WRITE TOOL:
    Must only execute through the confirmed
    write executor.
    """

    if (
        isinstance(lead_id, bool)
        or not isinstance(lead_id, int)
        or lead_id <= 0
    ):
        return {
            "success": False,
            "error": {
                "code": "INVALID_LEAD_ID",
                "message": (
                    "A valid positive lead ID is required."
                ),
            },
        }

    if activity_type != "note":
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_ACTIVITY_TYPE",
                "message": (
                    "Only CRM note creation is enabled."
                ),
            },
        }

    if (
        not isinstance(description, str)
        or not description.strip()
    ):
        return {
            "success": False,
            "error": {
                "code": "INVALID_NOTE",
                "message": (
                    "A non-empty lead note is required."
                ),
            },
        }

    cleaned_description = (
        description.strip()
    )

    if len(cleaned_description) > settings.CRM_NOTE_MAX_LENGTH:
        return {
            "success": False,
            "error": {
                "code": "NOTE_TOO_LONG",
                "message": (
                    "Lead note exceeds the maximum length of "
                    f"{settings.CRM_NOTE_MAX_LENGTH} characters."
                ),
            },
        }

    lead = lead_services.get_lead_by_id(
        lead_id=lead_id,
    )

    if lead is None:
        return {
            "success": False,
            "error": {
                "code": "LEAD_NOT_FOUND",
                "message": (
                    f"Lead {lead_id} was not found."
                ),
            },
        }

    activity = lead_services.create_lead_note(
        lead=lead,
        description=cleaned_description,
    )

    verified_activity = (
        lead_services.get_lead_activity_by_id(
            activity_id=activity.id,
        )
    )

    if (
        verified_activity is None
        or verified_activity.lead_id != lead.id
        or verified_activity.activity_type != "note"
        or verified_activity.description
        != cleaned_description
    ):
        return {
            "success": False,
            "error": {
                "code": (
                    "LEAD_NOTE_VERIFICATION_FAILED"
                ),
                "message": (
                    "The new CRM note could not "
                    "be verified."
                ),
            },
        }

    return {
        "success": True,
        "data": {
            "activity_id": (
                verified_activity.id
            ),
            "lead_id": lead.id,
            "company_name": (
                lead.company_name
            ),
            "activity_type": (
                verified_activity.activity_type
            ),
            "description": (
                verified_activity.description
            ),
        },
    }