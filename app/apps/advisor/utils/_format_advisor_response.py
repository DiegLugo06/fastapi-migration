"""
Format advisor response utility
Migrated from Flask
"""
from app.apps.authentication.models import User


def _format_advisor_response(advisor: User) -> dict:
    """Format advisor data for API response."""
    return {
        "id": advisor.id,
        "uuid": str(advisor.uuid),
        "name": advisor.name,
        "second_name": advisor.second_name,
        "first_last_name": advisor.first_last_name,
        "second_last_name": advisor.second_last_name,
        "email": advisor.email,
        "zona_autoestrena_url": advisor.zona_autoestrena_url,
        "selected_at": advisor.last_selected_at.isoformat() if advisor.last_selected_at else None,
        "role_id": advisor.role_id,
        "phone_number": advisor.phone_number,
    }

