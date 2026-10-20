"""Login and project-permission checks used by the routers.

Pages that need a login start with:
    redirect = require_login(request)
    if redirect:
        return redirect
"""

from fastapi import Request
from fastapi.responses import RedirectResponse


def require_login(request: Request):
    """Send the user to /login if they are not logged in (returns None when they are)."""
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login", status_code=303)
    return None


def get_allowed_projects(request: Request):
    """Returns None if the user can see everything (admin), or a list of
    allowed project names to filter by."""
    if request.session.get("is_admin"):
        return None
    return request.session.get("projects", [])
