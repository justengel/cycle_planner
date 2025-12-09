from fastapi import APIRouter, HTTPException, Depends, Request, Response
from pydantic import BaseModel, EmailStr

from app.services.supabase import get_supabase_client, SupabaseClient

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    access_token: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    user_id: str
    email: str


@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignupRequest, client: SupabaseClient = Depends(get_supabase_client)):
    try:
        response = client.auth.sign_up({
            "email": request.email,
            "password": request.password,
        })
        if response.user is None:
            raise HTTPException(status_code=400, detail="Signup failed")
        return AuthResponse(
            access_token=response.session.access_token if response.session else "",
            user_id=response.user.id,
            email=response.user.email,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(request: LoginRequest, response: Response, client: SupabaseClient = Depends(get_supabase_client)):
    try:
        auth_response = client.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password,
        })
        if auth_response.user is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Set auth cookies
        response.set_cookie(
            key="access_token",
            value=auth_response.session.access_token,
            httponly=True,
            max_age=auth_response.session.expires_in,
            samesite="lax"
        )
        response.set_cookie(
            key="refresh_token",
            value=auth_response.session.refresh_token,
            httponly=True,
            max_age=60 * 60 * 24 * 30,  # 30 days
            samesite="lax"
        )

        return {
            "user_id": auth_response.user.id,
            "email": auth_response.user.email,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    response.delete_cookie("spotify_access_token")
    response.delete_cookie("spotify_refresh_token")
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_user(request: Request, client: SupabaseClient = Depends(get_supabase_client)):
    """Get current logged-in user info."""
    access_token = request.cookies.get("access_token")
    if not access_token:
        return {"authenticated": False}

    try:
        # Verify token with Supabase
        user_response = client.auth.get_user(access_token)
        if user_response and user_response.user:
            return {
                "authenticated": True,
                "user_id": user_response.user.id,
                "email": user_response.user.email,
            }
    except Exception:
        pass

    return {"authenticated": False}


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, client: SupabaseClient = Depends(get_supabase_client)):
    """Send a password reset email."""
    try:
        client.auth.reset_password_email(request.email)
        return {"message": "Password reset email sent"}
    except Exception as e:
        # Don't reveal if email exists or not for security
        return {"message": "Password reset email sent"}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, client: SupabaseClient = Depends(get_supabase_client)):
    """Reset password using the token from email."""
    try:
        # Use the access token to update the user's password
        client.auth.admin.update_user_by_id(
            client.auth.get_user(request.access_token).user.id,
            {"password": request.password}
        )
        return {"message": "Password reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to reset password. Link may be expired.")
