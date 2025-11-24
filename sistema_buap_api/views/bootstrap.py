import os

from django.conf import settings
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView


class VersionView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    # GET: devuelve la versión actual de la aplicación
    def get(self, request, *args, **kwargs):
        version = getattr(settings, "APP_VERSION", os.getenv("APP_VERSION", "1.0.0"))
        return Response({"version": version})
