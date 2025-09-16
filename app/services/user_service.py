from app.api.deps.db_deps import get_db_session
from app.core.exceptions import InternalServerErrorException
from app.db.models import User


async def create_user_and_generate_api_key(**kwargs) -> str:
    try:
        async for session in get_db_session():
            user = await User.create(
                session=session,
                email=kwargs.get("email", ""),
                first_name=kwargs.get("first_name", ""),
                last_name=kwargs.get("last_name", ""),
            )
            return user.api_key
    except Exception as e:
        raise InternalServerErrorException(f"Invalid request data: {str(e)}")
