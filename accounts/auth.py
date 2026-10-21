"""JWT-in-HTTP-only-cookie authentication with CSRF enforcement."""
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication, CSRFCheck
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

User = get_user_model()

def issue_token(user):
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_TTL_HOURS)
    return jwt.encode({"sub": str(user.pk), "exp": exp}, settings.SECRET_KEY, algorithm="HS256")

def set_auth_cookie(response, user):
    response.set_cookie(settings.JWT_COOKIE, issue_token(user),
                        max_age=settings.JWT_TTL_HOURS * 3600, httponly=True,
                        secure=settings.COOKIE_SECURE, samesite="Lax")
    return response

class CookieJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = request.COOKIES.get(settings.JWT_COOKIE)
        if not token:
            return None
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user = User.objects.get(pk=int(payload["sub"]), is_active=True)
        except (jwt.PyJWTError, User.DoesNotExist, KeyError, ValueError):
            raise AuthenticationFailed("Invalid or expired session.")
        self._enforce_csrf(request)  # cookies are sent automatically, so require CSRF token
        return (user, token)

    def authenticate_header(self, request):
        return "Cookie"

    @staticmethod
    def _enforce_csrf(request):
        check = CSRFCheck(lambda r: None)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise PermissionDenied(f"CSRF failed: {reason}")
