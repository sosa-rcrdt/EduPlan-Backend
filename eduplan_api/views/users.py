from django.db import transaction
from django.db.models import *
from django.shortcuts import get_object_or_404, render
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.models import Group
from django.core import serializers
from django.utils.html import strip_tags
from django.conf import settings
from django.template.loader import render_to_string

from rest_framework import generics, permissions, status, viewsets
from rest_framework.authentication import BasicAuthentication, SessionAuthentication, TokenAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view
from rest_framework.generics import CreateAPIView, DestroyAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters

from datetime import datetime
import string
import random
import json

from eduplan_api.serializers import *
from eduplan_api.models import *


class AdminAll(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Obtener lista de administradores activos.
    def get(self, request, *args, **kwargs):
        admin = Administradores.objects.filter(user__is_active=1).order_by("id")
        lista = AdminSerializer(admin, many=True).data
        return Response(lista, 200)


class AdminView(generics.CreateAPIView):

    # Obtener administrador por ID
    def get(self, request, *args, **kwargs):
        admin = get_object_or_404(Administradores, id=request.GET.get("id"))
        admin = AdminSerializer(admin, many=False).data
        return Response(admin, 200)

    # Registrar nuevo administrador
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        user = UserSerializer(data=request.data)

        # Validar datos básicos usando el serializer de usuario
        if user.is_valid():
            # Datos del request
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

            # Asignar el rol mediante grupos
            group, created = Group.objects.get_or_create(name=role)
            group.user_set.add(user)
            user.save()

            # Crear perfil de administrador asociado al usuario
            admin = Administradores.objects.create(
                user=user,
                clave_admin=request.data["clave_admin"],
                telefono=request.data["telefono"],
                rfc=request.data["rfc"].upper(),
                edad=request.data["edad"],
                ocupacion=request.data["ocupacion"]
            )
            admin.save()

            return Response({"admin_created_id": admin.id}, 201)

        # Responder errores de validación del serializer
        return Response(user.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminsViewEdit(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Contar el total de administradores, maestros y alumnos activos.
    def get(self, request, *args, **kwargs):
        # Total de administradores
        admin = Administradores.objects.filter(user__is_active=1).order_by("id")
        lista_admins = AdminSerializer(admin, many=True).data
        total_admins = len(lista_admins)

        # Total de maestros
        maestros = Maestros.objects.filter(user__is_active=1).order_by("id")
        lista_maestros = MaestroSerializer(maestros, many=True).data

        # Si no hay maestros, regresar vacío
        if not lista_maestros:
            return Response({}, 400)

        # Convertir materias_json de string a estructura JSON
        for maestro in lista_maestros:
            maestro["materias_json"] = json.loads(maestro["materias_json"])

        total_maestros = len(lista_maestros)

        # Total de alumnos
        alumnos = Alumnos.objects.filter(user__is_active=1).order_by("id")
        lista_alumnos = AlumnoSerializer(alumnos, many=True).data
        total_alumnos = len(lista_alumnos)

        return Response(
            {
                'admins': total_admins,
                'maestros': total_maestros,
                'alumnos': total_alumnos
            },
            200
        )

    # Editar la información de un administrador
    def put(self, request, *args, **kwargs):
        admin = get_object_or_404(Administradores, id=request.data["id"])

        # Actualizar datos del perfil de administrador
        admin.clave_admin = request.data["clave_admin"]
        admin.telefono = request.data["telefono"]
        admin.rfc = request.data["rfc"]
        admin.edad = request.data["edad"]
        admin.ocupacion = request.data["ocupacion"]
        admin.save()

        # Actualizar datos del usuario asociado
        temp = admin.user
        temp.first_name = request.data["first_name"]
        temp.last_name = request.data["last_name"]
        temp.save()

        user = AdminSerializer(admin, many=False).data
        return Response(user, 200)

    # Eliminar un administrador:
    def delete(self, request, *args, **kwargs):
        admin = get_object_or_404(Administradores, id=request.GET.get("id"))

        try:
            admin.user.delete()
            return Response({"details": "Administrador eliminado"}, 200)
        except Exception as e:
            return Response({"details": "Algo pasó al eliminar"}, 400)

class ProfileView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Devuelve el perfil del usuario autenticado según su rol
    def get(self, request, *args, **kwargs):
        user = request.user
        roles = list(user.groups.values_list("name", flat=True))
        rol = roles[0] if roles else None

        if rol == "administrador":
            perfil = Administradores.objects.filter(user=user).first()
            if not perfil:
                return Response({"details": "No se encontró perfil de administrador"}, 400)
            data = AdminSerializer(perfil, many=False).data

        elif rol == "alumno":
            perfil = Alumnos.objects.filter(user=user).first()
            if not perfil:
                return Response({"details": "No se encontró perfil de alumno"}, 400)
            data = AlumnoSerializer(perfil, many=False).data

        elif rol == "maestro":
            perfil = Maestros.objects.filter(user=user).first()
            if not perfil:
                return Response({"details": "No se encontró perfil de maestro"}, 400)
            data = MaestroSerializer(perfil, many=False).data

        else:
            return Response({"details": "Rol no soportado o no asignado"}, 403)

        data["rol"] = rol
        return Response(data, 200)

    # Actualiza el perfil del usuario autenticado según su rol
    @transaction.atomic
    def put(self, request, *args, **kwargs):
        user = request.user
        roles = list(user.groups.values_list("name", flat=True))
        rol = roles[0] if roles else None

        if rol == "administrador":
            perfil = Administradores.objects.filter(user=user).first()
            if not perfil:
                return Response({"details": "No se encontró perfil de administrador"}, 400)

            perfil.clave_admin = request.data.get("clave_admin", perfil.clave_admin)
            perfil.telefono = request.data.get("telefono", perfil.telefono)
            perfil.rfc = request.data.get("rfc", perfil.rfc)
            perfil.edad = request.data.get("edad", perfil.edad)
            perfil.ocupacion = request.data.get("ocupacion", perfil.ocupacion)
            perfil.save()

        elif rol == "alumno":
            perfil = Alumnos.objects.filter(user=user).first()
            if not perfil:
                return Response({"details": "No se encontró perfil de alumno"}, 400)

            perfil.matricula = request.data.get("matricula", perfil.matricula)
            curp = request.data.get("curp")
            if curp is not None:
                perfil.curp = curp.upper()
            rfc = request.data.get("rfc")
            if rfc is not None:
                perfil.rfc = rfc.upper()
            perfil.fecha_nacimiento = request.data.get("fecha_nacimiento", perfil.fecha_nacimiento)
            perfil.edad = request.data.get("edad", perfil.edad)
            perfil.telefono = request.data.get("telefono", perfil.telefono)
            perfil.ocupacion = request.data.get("ocupacion", perfil.ocupacion)
            perfil.save()

        elif rol == "maestro":
            perfil = Maestros.objects.filter(user=user).first()
            if not perfil:
                return Response({"details": "No se encontró perfil de maestro"}, 400)

            perfil.id_trabajador = request.data.get("id_trabajador", perfil.id_trabajador)
            perfil.fecha_nacimiento = request.data.get("fecha_nacimiento", perfil.fecha_nacimiento)
            perfil.telefono = request.data.get("telefono", perfil.telefono)
            perfil.rfc = request.data.get("rfc", perfil.rfc)
            perfil.cubiculo = request.data.get("cubiculo", perfil.cubiculo)
            perfil.area_investigacion = request.data.get("area_investigacion", perfil.area_investigacion)

            materias_json = request.data.get("materias_json")
            if materias_json is not None:
                # se guarda la lista de materias como string JSON
                perfil.materias_json = json.dumps(materias_json)

            perfil.save()

        else:
            return Response({"details": "Rol no soportado o no asignado"}, 403)

        # Actualizar nombre del usuario si viene en la petición
        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if first_name is not None or last_name is not None:
            user.save()

        # Devolver perfil actualizado
        if rol == "administrador":
            data = AdminSerializer(perfil, many=False).data
        elif rol == "alumno":
            data = AlumnoSerializer(perfil, many=False).data
        else:
            data = MaestroSerializer(perfil, many=False).data

        data["rol"] = rol
        return Response(data, 200)
