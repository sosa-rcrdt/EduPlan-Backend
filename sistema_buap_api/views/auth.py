from django.db.models import *
from django.shortcuts import render
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.models import Group
from django.core import serializers
from django.utils.html import strip_tags
from django.conf import settings
from django.template.loader import render_to_string

from rest_framework import generics, permissions, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view
from rest_framework.generics import CreateAPIView, DestroyAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework_simplejwt.views import TokenObtainPairView

from datetime import datetime
import string
import random

from sistema_buap_api.serializers import (
    CustomTokenObtainPairSerializer,
)
from sistema_buap_api.models import *


class LoginJWTView(TokenObtainPairView):
    # Usar el serializador personalizado para login JWT
    serializer_class = CustomTokenObtainPairSerializer


class Logout(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Logout lógico: el frontend debe borrar el token
    def get(self, request, *args, **kwargs):
        return Response({"logout": True}, status=status.HTTP_200_OK)


class ChangePasswordView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Cambiar la contraseña del usuario logueado
    def put(self, request, *args, **kwargs):
        user = request.user

        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        # Validar que vengan todos los campos
        if not current_password or not new_password or not confirm_password:
            return Response(
                {"details": "Debe enviar current_password, new_password y confirm_password"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar coincidencia de nueva y confirmación
        if new_password != confirm_password:
            return Response(
                {"details": "La nueva contraseña y su confirmación no coinciden"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verificar contraseña actual
        if not user.check_password(current_password):
            return Response(
                {"details": "La contraseña actual es incorrecta"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar que la nueva contraseña NO sea igual a la actual
        if current_password == new_password:
            return Response(
                {"details": "La nueva contraseña no puede ser igual a la contraseña actual"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validaciones extra (longitud mínima, etc.)
        if len(new_password) < 8:
            return Response(
                {"details": "La nueva contraseña debe tener al menos 8 caracteres"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Actualizar contraseña
        user.set_password(new_password)
        user.save()

        return Response(
            {"details": "Contraseña actualizada correctamente"},
            status=status.HTTP_200_OK,
        )
