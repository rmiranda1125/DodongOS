from django.core import signing


PROPOSAL_SIGNING_SALT = (
    "apps.ai.crm_action_proposal.v1"
)


def sign_action_proposal(proposal):
    """
    Sign a validated CRM action proposal.

    The browser may carry this token, but cannot safely
    modify its contents without invalidating the signature.
    """

    if not isinstance(proposal, dict):
        raise ValueError(
            "proposal must be a dictionary"
        )

    return signing.dumps(
        proposal,
        salt=PROPOSAL_SIGNING_SALT,
        compress=True,
    )


def load_action_proposal(
    token,
    *,
    max_age=600,
):
    """
    Verify and deserialize a signed action proposal.

    max_age defaults to 10 minutes.
    """

    try:
        proposal = signing.loads(
            token,
            salt=PROPOSAL_SIGNING_SALT,
            max_age=max_age,
        )

    except signing.SignatureExpired:
        return {
            "success": False,
            "error": {
                "code": "PROPOSAL_EXPIRED",
                "message": (
                    "This CRM action proposal has expired. "
                    "Please create a new proposal."
                ),
            },
        }

    except signing.BadSignature:
        return {
            "success": False,
            "error": {
                "code": "INVALID_PROPOSAL_TOKEN",
                "message": (
                    "The CRM action proposal could not "
                    "be verified."
                ),
            },
        }

    if not isinstance(proposal, dict):
        return {
            "success": False,
            "error": {
                "code": "INVALID_PROPOSAL_TOKEN",
                "message": (
                    "The CRM action proposal is invalid."
                ),
            },
        }

    return {
        "success": True,
        "proposal": proposal,
    }