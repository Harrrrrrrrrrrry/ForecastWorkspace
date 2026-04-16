from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.schemas import (
    AdminApproveUserRequest,
    AdminApproveUserResponse,
    AuthUserResponse,
    SignInRequest,
    SignInResponse,
    SignUpRequest,
    SignUpResponse,
    UserStatus,
)
from app.services.auth import AuthUser, auth_service


router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


def _serialize_user(user: AuthUser) -> AuthUserResponse:
    return AuthUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        access_reason=user.access_reason,
        status=user.status,
        role=user.role,
        created_at=user.created_at,
        approved_at=user.approved_at,
    )


def get_current_approved_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
        )

    user = auth_service.get_user_by_token(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is invalid or expired.",
        )

    if user.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not approved for GPT explanation access.",
        )

    return user


def get_current_admin_user(current_user: AuthUser = Depends(get_current_approved_user)) -> AuthUser:
    if current_user.role not in {"owner", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required.",
        )

    return current_user


@router.post("/sign-up", response_model=SignUpResponse, status_code=status.HTTP_201_CREATED)
def sign_up(payload: SignUpRequest) -> SignUpResponse:
    try:
        user = auth_service.create_user(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            access_reason=payload.access_reason,
        )
    except ValueError as exc:
        status_code = status.HTTP_409_CONFLICT if "already exists" in str(exc).lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    return SignUpResponse(
        message="Your account has been created. You can sign in immediately.",
        user=_serialize_user(user),
    )


@router.post("/sign-in", response_model=SignInResponse)
def sign_in(payload: SignInRequest) -> SignInResponse:
    try:
        token, user = auth_service.authenticate_user(email=payload.email, password=payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return SignInResponse(
        message="Sign-in succeeded.",
        token=token,
        user=_serialize_user(user),
    )


@router.get("/me", response_model=AuthUserResponse)
def get_current_user(current_user: AuthUser = Depends(get_current_approved_user)) -> AuthUserResponse:
    return _serialize_user(current_user)


@router.get("/admin/users", response_model=list[AuthUserResponse])
def list_users(
    status_filter: UserStatus | None = Query(default=None, alias="status"),
    current_user: AuthUser = Depends(get_current_admin_user),
) -> list[AuthUserResponse]:
    _ = current_user
    return [_serialize_user(user) for user in auth_service.list_users(status=status_filter)]


@router.post(
    "/admin/approve",
    response_model=AdminApproveUserResponse,
)
def approve_user(
    payload: AdminApproveUserRequest,
    current_user: AuthUser = Depends(get_current_admin_user),
) -> AdminApproveUserResponse:
    _ = current_user
    try:
        user = auth_service.approve_user(email=payload.email)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return AdminApproveUserResponse(
        message="User access approved.",
        user=_serialize_user(user),
    )
