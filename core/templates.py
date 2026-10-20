import jinja2
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")


def dash(value):
    """Template filter: {{ value | dash }} shows "—" for blank or missing values."""
    if value is None or isinstance(value, jinja2.Undefined) or value == "":
        return "—"
    return value


templates.env.filters["dash"] = dash
