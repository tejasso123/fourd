from contextvars import ContextVar
from app.db.models import User

# Context variable to store authenticated user per request
loggedin_user_var: ContextVar[User] = ContextVar("current_user")
