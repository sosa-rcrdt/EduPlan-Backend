from django.shortcuts import render, get_object_or_404
from django.db.models import *
from django.db import transaction
from django.conf import settings
from django.template.loader import render_to_string
from django.core import serializers
from django.utils.html import strip_tags

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

from eduplan_api.serializers import *
from eduplan_api.models import *


class HorariosAll(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Devuelve el listado de horarios (permite filtros por periodo, grupo, aula, docente y día)
    def get(self, request, *args, **kwargs):
        horarios = Horario.objects.all().order_by("dia_semana", "hora_inicio")

        periodo_id = request.GET.get("periodo_id")
        if periodo_id:
            horarios = horarios.filter(periodo_id=periodo_id)

        grupo_id = request.GET.get("grupo_id")
        if grupo_id:
            horarios = horarios.filter(grupo_id=grupo_id)

        aula_id = request.GET.get("aula_id")
        if aula_id:
            horarios = horarios.filter(aula_id=aula_id)

        docente_id = request.GET.get("docente_id")
        if docente_id:
            horarios = horarios.filter(docente_id=docente_id)

        dia_semana = request.GET.get("dia_semana")
        if dia_semana is not None:
            horarios = horarios.filter(dia_semana=dia_semana)

        lista = HorarioSerializer(horarios, many=True).data
        return Response(lista, 200)

    # Registra un nuevo horario validando periodo activo y que no existan choques
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = HorarioSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        periodo = serializer.validated_data["periodo"]
        grupo = serializer.validated_data["grupo"]
        aula = serializer.validated_data["aula"]
        docente = serializer.validated_data["docente"]
        dia_semana = serializer.validated_data["dia_semana"]
        hora_inicio = serializer.validated_data["hora_inicio"]
        hora_fin = serializer.validated_data["hora_fin"]

        # Validar que el periodo esté activo
        if periodo.estado != "ACTIVO":
            return Response(
                {"details": "Solo se pueden crear horarios en un periodo ACTIVO"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar que la hora de inicio sea menor a la hora fin
        if hora_inicio >= hora_fin:
            return Response(
                {"details": "La hora de inicio debe ser menor que la hora de fin"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar choques de aula en la misma franja
        choques_aula = Horario.objects.filter(
            periodo=periodo,
            aula=aula,
            dia_semana=dia_semana,
            estado="ACTIVO",
            hora_inicio__lt=hora_fin,
            hora_fin__gt=hora_inicio,
        )

        if choques_aula.exists():
            return Response(
                {"details": "El aula ya está ocupada en esa franja horaria"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar choques de docente en la misma franja
        choques_docente = Horario.objects.filter(
            periodo=periodo,
            docente=docente,
            dia_semana=dia_semana,
            estado="ACTIVO",
            hora_inicio__lt=hora_fin,
            hora_fin__gt=hora_inicio,
        )

        if choques_docente.exists():
            return Response(
                {"details": "El docente ya tiene un horario en esa franja"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        horario = serializer.save()
        return Response({"horario_created_id": horario.id}, status=status.HTTP_201_CREATED)


class HorarioView(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Obtiene la información de un horario por id
    def get(self, request, *args, **kwargs):
        horario = get_object_or_404(Horario, id=request.GET.get("id"))
        horario = HorarioSerializer(horario, many=False).data
        return Response(horario, 200)

    # Actualiza un horario validando periodo activo y evitando choques
    @transaction.atomic
    def put(self, request, *args, **kwargs):
        horario = get_object_or_404(Horario, id=request.data.get("id"))
        serializer = HorarioSerializer(horario, data=request.data, partial=True)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Tomar nuevos valores o conservar los actuales
        periodo = serializer.validated_data.get("periodo", horario.periodo)
        grupo = serializer.validated_data.get("grupo", horario.grupo)
        aula = serializer.validated_data.get("aula", horario.aula)
        docente = serializer.validated_data.get("docente", horario.docente)
        dia_semana = serializer.validated_data.get("dia_semana", horario.dia_semana)
        hora_inicio = serializer.validated_data.get("hora_inicio", horario.hora_inicio)
        hora_fin = serializer.validated_data.get("hora_fin", horario.hora_fin)

        # Validar que el periodo esté activo
        if periodo.estado != "ACTIVO":
            return Response(
                {"details": "Solo se pueden modificar horarios de un periodo ACTIVO"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar que la hora de inicio sea menor a la hora fin
        if hora_inicio >= hora_fin:
            return Response(
                {"details": "La hora de inicio debe ser menor que la hora de fin"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar choques de aula en la misma franja (excluyendo el horario actual)
        choques_aula = Horario.objects.filter(
            periodo=periodo,
            aula=aula,
            dia_semana=dia_semana,
            estado="ACTIVO",
            hora_inicio__lt=hora_fin,
            hora_fin__gt=hora_inicio,
        ).exclude(id=horario.id)

        if choques_aula.exists():
            return Response(
                {"details": "El aula ya está ocupada en esa franja horaria"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar choques de docente en la misma franja (excluyendo el horario actual)
        choques_docente = Horario.objects.filter(
            periodo=periodo,
            docente=docente,
            dia_semana=dia_semana,
            estado="ACTIVO",
            hora_inicio__lt=hora_fin,
            hora_fin__gt=hora_inicio,
        ).exclude(id=horario.id)

        if choques_docente.exists():
            return Response(
                {"details": "El docente ya tiene un horario en esa franja"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        horario = serializer.save()
        data = HorarioSerializer(horario, many=False).data
        return Response(data, 200)

    # Elimina un horario por id
    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        horario = get_object_or_404(Horario, id=request.GET.get("id"))
        try:
            horario.delete()
            return Response({"details": "Horario eliminado"}, 200)
        except Exception:
            return Response({"details": "Algo pasó al eliminar el horario"}, 400)


class HorariosDocenteView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Devuelve los horarios del docente logueado (permite filtrar por periodo y día)
    def get(self, request, *args, **kwargs):
        user = request.user
        maestro = Maestros.objects.filter(user=user).first()

        if not maestro:
            return Response(
                {"details": "El usuario autenticado no tiene perfil de maestro"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        horarios = Horario.objects.filter(docente=maestro).order_by(
            "dia_semana", "hora_inicio"
        )

        periodo_id = request.GET.get("periodo_id")
        if periodo_id:
            horarios = horarios.filter(periodo_id=periodo_id)

        dia_semana = request.GET.get("dia_semana")
        if dia_semana is not None:
            horarios = horarios.filter(dia_semana=dia_semana)

        data = HorarioSerializer(horarios, many=True).data
        return Response(data, 200)
