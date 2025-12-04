from django.shortcuts import render, get_object_or_404
from django.db.models import *
from django.db import transaction
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.models import Group
from django.core import serializers
from django.utils.html import strip_tags
from django.conf import settings
from django.template.loader import render_to_string

from rest_framework.authentication import BasicAuthentication, SessionAuthentication, TokenAuthentication
from rest_framework.generics import CreateAPIView, DestroyAPIView, UpdateAPIView
from rest_framework import permissions, generics, status, viewsets
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse

from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters

from datetime import datetime
import string
import random
import json

from eduplan_api.serializers import *
from eduplan_api.models import *


class MaestrosAll(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Devuelve el listado de maestros activos, incluyendo materias_json parseado
    def get(self, request, *args, **kwargs):
        maestros = Maestros.objects.filter(user__is_active=1).order_by("id")
        maestros = MaestroSerializer(maestros, many=True).data

        if not maestros:
            return Response({}, 400)

        for maestro in maestros:
            if maestro["materias_json"]:
                maestro["materias_json"] = json.loads(maestro["materias_json"])
            else:
                maestro["materias_json"] = []

        return Response(maestros, 200)


class MaestrosView(generics.CreateAPIView):
    # Define los permisos según el método HTTP
    def get_permissions(self):
        # POST (registro) SIN autenticación
        if self.request.method == "POST":
            return [permissions.AllowAny()]
        # GET (ver alumno por id) SÍ requiere token
        return [permissions.IsAuthenticated()]

    # Obtiene la información de un maestro por id
    def get(self, request, *args, **kwargs):
        maestro = get_object_or_404(Maestros, id=request.GET.get("id"))
        maestro = MaestroSerializer(maestro, many=False).data
        if maestro["materias_json"]:
            maestro["materias_json"] = json.loads(maestro["materias_json"])
        else:
            maestro["materias_json"] = []
        return Response(maestro, 200)

    # Registra un nuevo maestro y su usuario asociado
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        user = UserSerializer(data=request.data)

        if user.is_valid():
            # Datos básicos del usuario
            role = request.data['rol']
            first_name = request.data['first_name']
            last_name = request.data['last_name']
            email = request.data['email']
            password = request.data['password']

            # Validar que el email no esté ya registrado
            existing_user = User.objects.filter(email=email).first()
            if existing_user:
                return Response({"message": "Username " + email + ", is already taken"}, 400)

            # Crear usuario base de Django
            user = User.objects.create(
                username=email,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=1
            )
            user.set_password(password)
            user.save()

            # Asignar rol mediante grupo
            group, created = Group.objects.get_or_create(name=role)
            group.user_set.add(user)
            user.save()

            # Crear perfil de maestro asociado
            maestro = Maestros.objects.create(
                user=user,
                id_trabajador=request.data["id_trabajador"],
                fecha_nacimiento=request.data["fecha_nacimiento"],
                telefono=request.data["telefono"],
                rfc=request.data["rfc"].upper(),
                cubiculo=request.data["cubiculo"],
                area_investigacion=request.data["area_investigacion"],
                materias_json=json.dumps(
                    request.data["materias_json"]
                )  # se guarda la lista como string JSON
            )
            maestro.save()

            return Response({"maestro_created_id": maestro.id}, 201)

        return Response(user.errors, status=status.HTTP_400_BAD_REQUEST)


class MaestrosViewEdit(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Actualiza la información de un maestro y su usuario asociado
    def put(self, request, *args, **kwargs):
        maestro = get_object_or_404(Maestros, id=request.data["id"])

        maestro.id_trabajador = request.data["id_trabajador"]
        maestro.fecha_nacimiento = request.data["fecha_nacimiento"]
        maestro.telefono = request.data["telefono"]
        maestro.rfc = request.data["rfc"]
        maestro.cubiculo = request.data["cubiculo"]
        maestro.area_investigacion = request.data["area_investigacion"]
        maestro.materias_json = json.dumps(
            request.data["materias_json"]
        )  # se actualiza la lista de materias como string JSON
        maestro.save()

        temp = maestro.user
        temp.first_name = request.data["first_name"]
        temp.last_name = request.data["last_name"]
        temp.save()

        user = MaestroSerializer(maestro, many=False).data
        return Response(user, 200)

    # Elimina al maestro y su usuario asociado
    def delete(self, request, *args, **kwargs):
        profile = get_object_or_404(Maestros, id=request.GET.get("id"))
        try:
            profile.user.delete()
            return Response({"details": "Maestro eliminado"}, 200)
        except Exception as e:
            return Response({"details": "Algo pasó al eliminar"}, 400)
