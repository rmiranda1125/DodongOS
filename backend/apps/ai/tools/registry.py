from dataclasses import dataclass
from typing import Any, Callable


from apps.ai.tools.crm.activities import (
    get_lead_activities_tool,
)


from apps.ai.tools.crm.leads import (
    change_lead_status_tool,
    get_lead_tool,
    search_leads_tool,
)


from apps.ai.tools.crm.pipeline import (
    get_pipeline_summary_tool,
)


from apps.ai.tools.crm.tasks import (
    get_lead_tasks_tool,
    get_overdue_tasks_tool,
    get_pending_tasks_tool,
    get_priority_tasks_tool,
    create_lead_task_tool,
    complete_lead_task_tool,
)


@dataclass(frozen=True)
class ToolDefinition:
    """
    Metadata for one AI-accessible tool.

    The registry does not contain agent reasoning or provider logic.
    """

    name: str
    description: str
    access_level: str
    function: Callable[..., dict]
    input_schema: dict[str, Any]


TOOL_REGISTRY = {

    # =========================================================
    # READ TOOLS
    # =========================================================

    "get_priority_tasks": ToolDefinition(
        name="get_priority_tasks",
        description=(
            "Return the highest-priority actionable CRM tasks."
        ),
        access_level="read",
        function=get_priority_tasks_tool,
        input_schema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 10,
                },
            },
            "additionalProperties": False,
        },
    ),


    "get_overdue_tasks": ToolDefinition(
        name="get_overdue_tasks",
        description="Return overdue CRM tasks.",
        access_level="read",
        function=get_overdue_tasks_tool,
        input_schema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 50,
                },
            },
            "additionalProperties": False,
        },
    ),


    "get_pending_tasks": ToolDefinition(
        name="get_pending_tasks",
        description=(
            "Return pending and in-progress CRM tasks."
        ),
        access_level="read",
        function=get_pending_tasks_tool,
        input_schema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 50,
                },
                "priority": {
                    "type": ["string", "null"],
                    "enum": [
                        "low",
                        "medium",
                        "high",
                        "urgent",
                        None,
                    ],
                },
            },
            "additionalProperties": False,
        },
    ),


    "get_lead_tasks": ToolDefinition(
        name="get_lead_tasks",
        description="Return tasks belonging to one CRM lead.",
        access_level="read",
        function=get_lead_tasks_tool,
        input_schema={
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "integer",
                    "minimum": 1,
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 50,
                },
                "status": {
                    "type": ["string", "null"],
                    "enum": [
                        "pending",
                        "in_progress",
                        "completed",
                        "cancelled",
                        None,
                    ],
                },
                "priority": {
                    "type": ["string", "null"],
                    "enum": [
                        "low",
                        "medium",
                        "high",
                        "urgent",
                        None,
                    ],
                },
            },
            "required": ["lead_id"],
            "additionalProperties": False,
        },
    ),


    "get_lead": ToolDefinition(
        name="get_lead",
        description="Return one CRM lead by ID.",
        access_level="read",
        function=get_lead_tool,
        input_schema={
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "integer",
                    "minimum": 1,
                },
            },
            "required": ["lead_id"],
            "additionalProperties": False,
        },
    ),


    "search_leads": ToolDefinition(
        name="search_leads",
        description=(
            "Search CRM leads using business and status filters."
        ),
        access_level="read",
        function=search_leads_tool,
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": ["string", "null"],
                },
                "status": {
                    "type": ["string", "null"],
                    "enum": [
                        "new",
                        "contacted",
                        "qualified",
                        "proposal",
                        "won",
                        "lost",
                        None,
                    ],
                },
                "country": {
                    "type": ["string", "null"],
                },
                "industry": {
                    "type": ["string", "null"],
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 20,
                },
            },
            "additionalProperties": False,
        },
    ),


    "get_lead_activities": ToolDefinition(
        name="get_lead_activities",
        description=(
            "Return activity history belonging to one CRM lead."
        ),
        access_level="read",
        function=get_lead_activities_tool,
        input_schema={
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "integer",
                    "minimum": 1,
                },
                "activity_type": {
                    "type": ["string", "null"],
                    "enum": [
                        "note",
                        "call",
                        "email",
                        "meeting",
                        "follow_up",
                        "status_changed",
                        None,
                    ],
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 50,
                },
            },
            "required": ["lead_id"],
            "additionalProperties": False,
        },
    ),


    "get_pipeline_summary": ToolDefinition(
        name="get_pipeline_summary",
        description="Return a summary of the CRM pipeline.",
        access_level="read",
        function=get_pipeline_summary_tool,
        input_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    ),


    # =========================================================
    # APPROVED WRITE TOOLS
    # =========================================================

    "create_lead_task": ToolDefinition(
        name="create_lead_task",
        description=(
            "Create one confirmed follow-up task "
            "for an existing CRM lead."
        ),
        access_level="write",
        function=create_lead_task_tool,
        input_schema={
            "lead_id": "integer",
            "title": "string",
            "description": "string",
            "task_type": "string",
            "priority": "string",
            "due_date": "string|null",
        },
    ),


    "complete_lead_task": ToolDefinition(
        name="complete_lead_task",
        description=(
            "Complete one explicitly confirmed CRM task."
        ),
        access_level="write",
        function=complete_lead_task_tool,
        input_schema={
            "task_id": "integer",
        },
    ),


    "change_lead_status": ToolDefinition(
        name="change_lead_status",
        description=(
            "Change one explicitly confirmed CRM "
            "lead status."
        ),
        access_level="write",
        function=change_lead_status_tool,
        input_schema={
            "lead_id": "integer",
            "status": "string",
            "expected_status": "string",
        },
    ),
}


def get_registered_tool(name):
    """
    Return a registered tool definition.

    Returns None when the tool name is unknown.
    """

    return TOOL_REGISTRY.get(name)


def list_registered_tools():
    """
    Return JSON-safe tool metadata.

    Callable Python functions are intentionally excluded.
    """

    return [
        {
            "name": tool.name,
            "description": tool.description,
            "access_level": tool.access_level,
            "input_schema": tool.input_schema,
        }
        for tool in TOOL_REGISTRY.values()
    ]


def execute_registered_tool(
    *,
    name,
    arguments=None,
):
    """
    Execute one registered tool.

    This is a controlled dispatcher, not an AI agent runtime.

    Only tools explicitly present in TOOL_REGISTRY may execute.
    """

    if not isinstance(name, str) or not name.strip():

        return {
            "success": False,
            "error": {
                "code": "INVALID_TOOL_NAME",
                "message": "Tool name must be a non-empty string.",
            },
        }


    tool = get_registered_tool(
        name.strip(),
    )


    if tool is None:

        return {
            "success": False,
            "error": {
                "code": "TOOL_NOT_FOUND",
                "message": (
                    f"Tool '{name}' is not registered."
                ),
            },
        }


    if tool.access_level != "read":

        return {
            "success": False,
            "error": {
                "code": "TOOL_ACCESS_DENIED",
                "message": (
                    f"Tool '{name}' is not permitted "
                    "in the read-only registry."
                ),
            },
        }


    if arguments is None:

        arguments = {}


    if not isinstance(arguments, dict):

        return {
            "success": False,
            "error": {
                "code": "INVALID_TOOL_ARGUMENTS",
                "message": "Tool arguments must be an object.",
            },
        }


    try:

        return tool.function(
            **arguments,
        )


    except TypeError:

        return {
            "success": False,
            "error": {
                "code": "INVALID_TOOL_ARGUMENTS",
                "message": (
                    f"Invalid arguments for tool '{name}'."
                ),
            },
        }


    except Exception:

        return {
            "success": False,
            "error": {
                "code": "TOOL_EXECUTION_ERROR",
                "message": (
                    f"Unable to execute tool '{name}'."
                ),
            },
        }


def execute_confirmed_write_tool(
    *,
    name,
    arguments=None,
    confirmed=False,
):
    """
    Execute a registered WRITE tool only after explicit
    confirmation.

    This path is intentionally separate from the normal
    read-only tool executor.
    """

    tool = get_registered_tool(
        name,
    )


    if tool is None:

        return {
            "success": False,
            "error": {
                "code": "TOOL_NOT_FOUND",
                "message": (
                    f"Tool '{name}' is not registered."
                ),
            },
        }


    if tool.access_level != "write":

        return {
            "success": False,
            "error": {
                "code": "WRITE_TOOL_REQUIRED",
                "message": (
                    "Confirmed write execution may only "
                    "run registered write tools."
                ),
            },
        }


    if confirmed is not True:

        return {
            "success": False,
            "error": {
                "code": "CONFIRMATION_REQUIRED",
                "message": (
                    "Explicit confirmation is required "
                    "before executing this CRM action."
                ),
            },
        }


    if arguments is None:

        arguments = {}


    if not isinstance(arguments, dict):

        return {
            "success": False,
            "error": {
                "code": "INVALID_TOOL_ARGUMENTS",
                "message": (
                    "Tool arguments must be provided "
                    "as a dictionary."
                ),
            },
        }


    try:

        return tool.function(
            **arguments,
        )


    except TypeError as exc:

        return {
            "success": False,
            "error": {
                "code": "INVALID_TOOL_ARGUMENTS",
                "message": str(exc),
            },
        }


    except Exception:

        return {
            "success": False,
            "error": {
                "code": "TOOL_EXECUTION_ERROR",
                "message": (
                    f"Unable to execute tool '{name}'."
                ),
            },
        }