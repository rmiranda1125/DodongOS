from apps.leads import services as lead_services


def get_pipeline_summary_tool():
    """
    Read-only CRM tool.

    Return a structured CRM pipeline summary using
    the CRM service layer.

    This function must never query Django models directly.
    """

    try:
        summary = lead_services.get_pipeline_summary()

        return {
            "success": True,
            "data": summary,
        }

    except Exception:
        return {
            "success": False,
            "error": {
                "code": "CRM_TOOL_ERROR",
                "message": "Unable to retrieve pipeline summary.",
            },
        }