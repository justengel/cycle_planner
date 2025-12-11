from fastapi import Depends, HTTPException, Request, Response
from starlette.responses import JSONResponse

from app.services.supabase import get_supabase_client, SupabaseClient


async def get_current_user_id(
    request: Request,
    client: SupabaseClient = Depends(get_supabase_client)
) -> str:
    """
    Extract and verify user ID from auth cookie.
    Automatically refreshes the token if expired but refresh token is valid.
    """
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")

    # Try with existing access token first
    if access_token:
        try:
            user_response = client.auth.get_user(access_token)
            if user_response and user_response.user:
                return user_response.user.id
        except Exception:
            pass  # Token expired or invalid, try refresh

    # No valid access token, try to refresh
    if refresh_token:
        try:
            new_session = client.auth.refresh_session(refresh_token)
            if new_session and new_session.session and new_session.user:
                # Store the new tokens in request state so middleware can set cookies
                request.state.new_access_token = new_session.session.access_token
                request.state.new_refresh_token = new_session.session.refresh_token
                request.state.token_expires_in = new_session.session.expires_in
                return new_session.user.id
        except Exception:
            pass  # Refresh token also invalid

    raise HTTPException(status_code=401, detail="Not authenticated")


async def get_optional_user_id(
    request: Request,
    client: SupabaseClient = Depends(get_supabase_client)
) -> str | None:
    """
    Same as get_current_user_id but returns None instead of raising exception.
    Useful for endpoints that work with or without authentication.
    """
    try:
        return await get_current_user_id(request, client)
    except HTTPException:
        return None
