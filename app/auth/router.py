
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

from datetime import timedelta

from app.auth.service import user_exists, create_user, get_user_by_email
from app.auth.schemas import UserCreateModel, UserResponseModel, UserLoginModel, RefreshTokenRequest
from fastapi.exceptions import HTTPException
from app.auth.utils import verify_password, create_access_token, decode_token
from app.database import async_session_local

auth_router = APIRouter(
    prefix="/auth",
    tags=["AUTH"],
)

REFRESH_TOKEN_EXPIRY = 7

@auth_router.post("/signup", response_model=UserResponseModel)
async def create_user_account(user: UserCreateModel):
    async with async_session_local() as session:
        email = user.email

        user_exist = await user_exists(email, session)

        if user_exist:
            raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User with email already exists",
        )

        new_user = await create_user(user, session)

    return new_user


@auth_router.post("/login")
async def login_users(data: UserLoginModel):
    async with async_session_local() as session:
        email = data.email
        password = data.password

        user = await get_user_by_email(email, session)

        if user is not None:
            valid = verify_password(password, user.password_hash)

            if valid:
                access_token = create_access_token(
                    user_data={"email": user.email, "user_uid": str(user.id)}
                )

                refresh_token = create_access_token(
                    user_data={"email": user.email, "user_uid": str(user.id)},
                    refresh=True,
                    expiry=timedelta(days=REFRESH_TOKEN_EXPIRY),
                )

                return JSONResponse(
                    content={
                        "message": "Login successful",
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "user": {"email": user.email, "uid": str(user.id)},
                    }
                )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Email Or Password"
    )

@auth_router.post("/refresh")
async def refresh_access_token(data: RefreshTokenRequest):

    payload = decode_token(data.refresh_token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if not payload.get("refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not a refresh token",
        )

    user_data = payload["user"]

    async with async_session_local() as session:
        user = await get_user_by_email(user_data["email"], session)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User no longer exists",
            )

    access_token = create_access_token(user_data=user_data)

    return JSONResponse(
        content={
            "message": "Token refreshed successfully",
            "access_token": access_token,
            "user": {
                "email": user.email,
                "uid": str(user.id),
            },
        }
    )