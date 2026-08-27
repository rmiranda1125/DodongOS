from apps.leads import services as lead_services


def _serialize_datetime(value):

    if value is None:

        return None

    return value.isoformat()


def _serialize_lead(lead):

    """
    Convert a Lead model instance into structured,
    JSON-safe data for AI consumption.
    """

    return {

        "id": lead.id,

        "company_name": lead.company_name,

        "website": lead.website,

        "industry": lead.industry,

        "country": lead.country,

        "job_title": lead.job_title,

        "source_url": lead.source_url,

        "source_platform": lead.source_platform,

        "work_setup": lead.work_setup,

        "employment_type": lead.employment_type,

        "location": lead.location,

        "salary": lead.salary,

        "lead_score": lead.lead_score,

        "ai_summary": lead.ai_summary,

        "recommended_services": lead.recommended_services,

        "pain_points": lead.pain_points,

        "status": lead.status,

        "created_at": _serialize_datetime(
            lead.created_at,
        ),

        "updated_at": _serialize_datetime(
            lead.updated_at,
        ),

    }


def get_lead_tool(*, lead_id):

    """
    Read-only CRM tool.

    Return one CRM lead using the CRM service layer.

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


    try:

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


        return {

            "success": True,

            "data": _serialize_lead(lead),

        }


    except Exception:

        return {

            "success": False,

            "error": {

                "code": "CRM_TOOL_ERROR",

                "message": "Unable to retrieve lead.",

            },

        }


def search_leads_tool(

    *,

    query=None,

    status=None,

    country=None,

    industry=None,

    limit=20,

):

    """
    Read-only CRM tool.

    Search leads through the CRM service layer.

    This function must never query Django models directly.
    """

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


    allowed_statuses = {

        "new",

        "contacted",

        "qualified",

        "proposal",

        "won",

        "lost",

    }


    if status is not None and status not in allowed_statuses:

        return {

            "success": False,

            "error": {

                "code": "INVALID_STATUS",

                "message": (

                    "status must be one of: "

                    "new, contacted, qualified, "

                    "proposal, won, lost."

                ),

            },

        }


    if query is not None and not isinstance(query, str):

        return {

            "success": False,

            "error": {

                "code": "INVALID_QUERY",

                "message": "query must be a string.",

            },

        }


    if country is not None and not isinstance(country, str):

        return {

            "success": False,

            "error": {

                "code": "INVALID_COUNTRY",

                "message": "country must be a string.",

            },

        }


    if industry is not None and not isinstance(industry, str):

        return {

            "success": False,

            "error": {

                "code": "INVALID_INDUSTRY",

                "message": "industry must be a string.",

            },

        }


    try:

        leads = lead_services.search_leads(

            query=query,

            status=status,

            country=country,

            industry=industry,

        )


        return {

            "success": True,

            "data": [

                _serialize_lead(lead)

                for lead in leads[:limit]

            ],

        }


    except Exception:

        return {

            "success": False,

            "error": {

                "code": "CRM_TOOL_ERROR",

                "message": "Unable to search leads.",

            },

        }


# =========================================================
# CHANGE LEAD STATUS
# =========================================================

ALLOWED_LEAD_STATUSES = {

    "new",

    "contacted",

    "qualified",

    "proposal",

    "won",

    "lost",

}


def change_lead_status_tool(

    *,

    lead_id,

    status,

    expected_status,

):

    """
    Change one CRM lead's status after explicit confirmation.

    WRITE TOOL:
    Must only run through the confirmed write executor.
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


    if (

        not isinstance(status, str)

        or not status.strip()

    ):

        return {

            "success": False,

            "error": {

                "code": "INVALID_LEAD_STATUS",

                "message": (

                    "A valid lead status is required."

                ),

            },

        }


    target_status = (

        status

        .strip()

        .lower()

    )


    if target_status not in ALLOWED_LEAD_STATUSES:

        return {

            "success": False,

            "error": {

                "code": "INVALID_LEAD_STATUS",

                "message": (

                    "The requested lead status "

                    "is not supported."

                ),

            },

        }


    if (

        not isinstance(expected_status, str)

        or expected_status not in ALLOWED_LEAD_STATUSES

    ):

        return {

            "success": False,

            "error": {

                "code": "INVALID_EXPECTED_LEAD_STATUS",

                "message": (

                    "The expected lead status "

                    "is invalid."

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


    #
    # Protect against a stale proposal.
    #

    if lead.status != expected_status:

        return {

            "success": False,

            "error": {

                "code": (

                    "LEAD_STATUS_CHANGED_SINCE_PROPOSAL"

                ),

                "message": (

                    "The lead status changed after "

                    "this proposal was prepared."

                ),

            },

        }


    if lead.status == target_status:

        return {

            "success": False,

            "error": {

                "code": "LEAD_ALREADY_IN_STATUS",

                "message": (

                    f"Lead {lead_id} is already "

                    f"in status '{target_status}'."

                ),

            },

        }


    previous_status = lead.status


    lead_services.change_lead_status(

        lead=lead,

        status=target_status,

    )


    verified_lead = (

        lead_services.get_lead_by_id(

            lead_id=lead_id,

        )

    )


    if (

        verified_lead is None

        or verified_lead.status != target_status

    ):

        return {

            "success": False,

            "error": {

                "code": (

                    "LEAD_STATUS_CHANGE_VERIFICATION_FAILED"

                ),

                "message": (

                    "The lead status change could "

                    "not be verified."

                ),

            },

        }


    return {

        "success": True,

        "data": {

            "lead_id": verified_lead.id,

            "company_name": (

                verified_lead.company_name

            ),

            "previous_status": previous_status,

            "status": verified_lead.status,

        },

    }