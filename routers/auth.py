"""Login, logout and adding users (admin only).

Logging in stores user_id, full_name, is_admin and the user's projects in the
session cookie; core/auth.py reads them back.
Tables: tbl_users, tbl_user_projects, tbl_projects.
"""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import bcrypt

from core.auth import require_login
from core.db import get_connection
from core.templates import templates

router = APIRouter()


# --- Login / logout ----------------------------------------------------------

@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    """Show the login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    """Check username and password, then store the user and their projects in the session."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, password_hash, full_name, is_admin FROM tbl_users WHERE username = %s", (username,))
    user = cur.fetchone()

    if not user or not bcrypt.checkpw(password.encode(), user[1].encode()):
        cur.close()
        conn.close()
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password."})

    cur.execute("SELECT project_name FROM tbl_user_projects WHERE user_id = %s", (user[0],))
    user_projects = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()

    request.session["user_id"] = user[0]
    request.session["full_name"] = user[2]
    request.session["is_admin"] = user[3]
    request.session["projects"] = user_projects

    return RedirectResponse(url="/", status_code=303)


@router.get("/logout")
def logout(request: Request):
    """Clear the session and go back to the home page."""
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


# --- Session check -----------------------------------------------------------

@router.get("/debug/session")
def debug_session(request: Request):
    """Show what is stored in the current session (for checking logins and project access)."""
    return {
        "user_id": request.session.get("user_id"),
        "full_name": request.session.get("full_name"),
        "is_admin": request.session.get("is_admin"),
        "projects": request.session.get("projects"),
    }


# --- Users (admin only) ------------------------------------------------------

@router.get("/admin/users/new", response_class=HTMLResponse)
def new_user_form(request: Request):
    """Form for adding a user (admins only)."""
    redirect = require_login(request)
    if redirect:
        return redirect
    if not request.session.get("is_admin"):
        return HTMLResponse("Admins only.", status_code=403)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT project_name FROM tbl_projects WHERE active = true ORDER BY project_name")
    projects = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()

    return templates.TemplateResponse("new_user.html", {"request": request, "projects": projects})


@router.post("/admin/users/new", response_class=HTMLResponse)
def submit_new_user(request: Request, username: str = Form(...), password: str = Form(...),
                     full_name: str = Form(...), is_admin: str = Form(None),
                     projects: list = Form(default=[])):
    """Create a user and give them access to the chosen projects (admins only)."""
    redirect = require_login(request)
    if redirect:
        return redirect
    if not request.session.get("is_admin"):
        return HTMLResponse("Admins only.", status_code=403)

    username = username.strip()
    full_name = full_name.strip()
    error = None
    success = None

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT project_name FROM tbl_projects WHERE active = true ORDER BY project_name")
    all_projects = [row[0] for row in cur.fetchall()]

    if not username or not password or not full_name:
        error = "Username, password, and full name are all required."
    else:
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        try:
            cur.execute(
                "INSERT INTO tbl_users (username, password_hash, full_name, is_admin) VALUES (%s, %s, %s, %s) RETURNING user_id",
                (username, password_hash, full_name, is_admin == "on")
            )
            new_user_id = cur.fetchone()[0]

            for project in projects:
                cur.execute(
                    "INSERT INTO tbl_user_projects (user_id, project_name) VALUES (%s, %s)",
                    (new_user_id, project)
                )
            conn.commit()
            success = f"User '{username}' created with access to: {', '.join(projects) if projects else 'no projects'}."
        except Exception as e:
            conn.rollback()
            error = str(e)

    cur.close()
    conn.close()
    return templates.TemplateResponse("new_user.html", {"request": request, "projects": all_projects, "error": error, "success": success})
