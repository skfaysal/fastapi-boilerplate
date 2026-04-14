from fastapi import APIRouter, status

from ..dependencies import CurrentUserDep, UserServiceDep
from ..schemas.user import UserResponse, UserVerification

router = APIRouter(prefix="/user", tags=["user"])


@router.get(
    "/",
    response_model=UserResponse,
    summary="Get my profile",
)
async def get_user(user: CurrentUserDep, service: UserServiceDep) -> UserResponse:
    return service.get_profile(user["id"])


@router.put(
    "/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change my password",
    responses={401: {"description": "Current password incorrect"}},
)
async def change_password(
    user: CurrentUserDep,
    service: UserServiceDep,
    data: UserVerification,
) -> None:
    service.change_password(user["id"], data)


@router.put(
    "/phonenumber/{phone_number}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update my phone number",
)
async def change_phone_number(
    user: CurrentUserDep,
    service: UserServiceDep,
    phone_number: str,
) -> None:
    service.change_phone_number(user["id"], phone_number)
