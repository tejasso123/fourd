import base64
import os
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models.base import Base
from sqlalchemy.exc import IntegrityError
from datetime import datetime


class User(Base):
    """
        User model to store Google OAuth user information.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    google_id = Column(String(100), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=True)
    profile_picture = Column(String(255), nullable=True)
    dim3 = Column(String(256), nullable=True)
    api_key = Column(String(128), nullable=False, unique=True, default=lambda: User.generate_api_key())

    def __repr__(self):
        return f"<User {self.email}>"

    def to_dict(self):
        return {"email": self.email, "profile_picture": self.profile_picture, "dim3": self.dim3,
                "api_key": self.api_key, "google_id": self.google_id, "id": self.id, "first_name": self.first_name,
                "last_name": self.last_name}

    @classmethod
    async def get_by_email(cls, session: AsyncSession, email: str):
        """
        Retrieve a user by email asynchronously.
        """
        stmt = select(cls).where(cls.email == email)
        result = await session.execute(stmt)
        return result.scalars().first()

    @classmethod
    async def get_by_api_key(cls, session: AsyncSession, api_key: str):
        """
        Retrieve a user by API key asynchronously.
        """
        stmt = select(cls).where(cls.api_key == api_key)
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    def generate_api_key():
        """Generate a secure random API key."""
        key = os.urandom(64)
        return base64.urlsafe_b64encode(key).decode('utf-8')

    @staticmethod
    def generate_dim3(email):
        """Generate dim3 field value."""
        # return f"dim3_{datetime.now(timezone.utc).strftime('%Y_%m_%dT%H_%M_%S')}_{email}"
        return f"dim3_{email}"

    @classmethod
    async def create(
            cls,
            session: AsyncSession,
            email: str,
            first_name: str,
            last_name: str,
            google_id: str = None,
            profile_picture: str = None,
    ):
        """
        Create and persist a new User record.

        Args:
            session (AsyncSession): SQLAlchemy async session.
            google_id (str): Google OAuth ID.
            email (str): User's email.
            first_name (str): User's first name.
            last_name (str, optional): User's last name.
            profile_picture (str, optional): Profile picture URL.

        Returns:
            User: The newly created User object, or None if creation failed.
        """
        # Check if email already exists
        existing_user = await cls.get_by_email(session, email)
        if existing_user:
            raise ValueError(f"User with email {email} already exists.")

        try:
            now = datetime.now()
            timestamp_str = now.strftime("%Y%m%d%H%M%S%f")
            new_user = cls(
                google_id=timestamp_str,
                email=email,
                first_name=first_name,
                last_name=last_name,
                profile_picture="-",
                dim3=cls.generate_dim3(email),
            )
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)

            return new_user

        except IntegrityError as e:
            await session.rollback()
            raise ValueError(f"IntegrityError while creating user: {e}")
