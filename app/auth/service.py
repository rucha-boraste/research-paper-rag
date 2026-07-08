from app.auth.models import User
from app.auth.schemas import UserCreateModel
from app.auth.utils import generate_password_hash
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

async def get_user_by_email(email: str, session: AsyncSession):
    statement = select(User).where(User.email == email)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    return user

async def user_exists(email: str, session: AsyncSession):
    user = await get_user_by_email(email,session)
    return True if user is not None else False

async def create_user(user: UserCreateModel, session: AsyncSession):
    user_dict = user.model_dump()
    new_user = User(
        username=user_dict["username"],
        email=user_dict["email"],
        password_hash=generate_password_hash(user_dict["password"]),
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    
    return new_user