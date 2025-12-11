from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class TokenRefreshMiddleware(BaseHTTPMiddleware):
    """
    Middleware to set refreshed token cookies on the response.
    Works with the get_current_user_id dependency which stores new tokens in request.state.
    """

    async def dispatch(self, request: Request, call_next):
        # Initialize state
        request.state.new_access_token = None
        request.state.new_refresh_token = None
        request.state.token_expires_in = None

        response = await call_next(request)

        # If tokens were refreshed during the request, set them in cookies
        if hasattr(request.state, 'new_access_token') and request.state.new_access_token:
            response.set_cookie(
                key="access_token",
                value=request.state.new_access_token,
                httponly=True,
                max_age=request.state.token_expires_in or 3600,
                samesite="lax"
            )
            if request.state.new_refresh_token:
                response.set_cookie(
                    key="refresh_token",
                    value=request.state.new_refresh_token,
                    httponly=True,
                    max_age=60 * 60 * 24 * 30,  # 30 days
                    samesite="lax"
                )

        return response
