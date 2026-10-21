from django.conf import settings
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
import logging

logger = logging.getLogger(__name__)

from .auth import set_auth_cookie
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer

@ensure_csrf_cookie
def csrf(request):
    """Sets the csrftoken cookie that the frontend echoes in X-CSRFToken."""
    return JsonResponse({"detail": "ok"})

class _PublicAuthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class RegisterView(_PublicAuthView):
    def post(self, request):
        try:
            s = RegisterSerializer(data=request.data)
            s.is_valid(raise_exception=True)
            user = s.save()
            response = Response(
                UserSerializer(user).data,
                status=status.HTTP_201_CREATED,
            )
            return set_auth_cookie(response, user)
        except Exception:
            logger.exception("Unexpected error in RegisterView")
            raise


class LoginView(_PublicAuthView):
    def post(self, request):
        try:
            s = LoginSerializer(data=request.data)
            s.is_valid(raise_exception=True)
            user = authenticate(
                username=s.validated_data["username"],
                password=s.validated_data["password"],
            )
            if not user:
                return Response(
                    {
                        "error": {
                            "status": 401,
                            "message": "Invalid username or password.",
                            "details": None,
                        }
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            response = Response(UserSerializer(user).data)
            return set_auth_cookie(response, user)
        except Exception:
            logger.exception("Unexpected error in LoginView")
            raise

class LogoutView(APIView):
    def post(self, request):
        resp = Response(status=status.HTTP_204_NO_CONTENT)
        resp.delete_cookie(settings.JWT_COOKIE)
        return resp

class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)
