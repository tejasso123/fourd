from fastapi import Depends, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import AuthenticationException, InternalServerErrorException
from app.api.deps.db_deps import get_db_session
from app.db.models import User
from app.core.context import loggedin_user_var

# Define the API key header (FastAPI automatically extracts it)
api_key_header = APIKeyHeader(name="x-api-key", auto_error=True)


async def require_auth(
        api_key: str = Security(api_key_header),
        session: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Dependency to validate API key before processing a request.
    """

    if not api_key:
        raise AuthenticationException("Missing API key")

    try:
        # Fetch user with the given API key
        user = await User.get_by_api_key(session, api_key)  # ✅ Using model method

        if not user:
            raise AuthenticationException("Invalid API key")

        # Define a context variable to store current_user
        loggedin_user_var.set(user)

        return user  # ✅ Returns authenticated user

    except Exception as e:
        print(f"Error validating API key: {str(e)}")
        raise InternalServerErrorException("An error occurred while validating API key")
