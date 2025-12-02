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


class PeriodosAll(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Devuelve el listado de períodos académicos
    def get(self, request, *args, **kwargs):
        periodos = PeriodoAcademico.objects.all().order_by("-fecha_inicio", "-id")
        lista = PeriodoAcademicoSerializer(periodos, many=True).data
        return Response(lista, 200)


class PeriodoView(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Obtiene la información de un período por id
    def get(self, request, *args, **kwargs):
        periodo = get_object_or_404(PeriodoAcademico, id=request.GET.get("id"))
        periodo = PeriodoAcademicoSerializer(periodo, many=False).data
        return Response(periodo, 200)

    # Registra un nuevo período académico
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = PeriodoAcademicoSerializer(data=request.data)

        if serializer.is_valid():
            fecha_inicio = serializer.validated_data["fecha_inicio"]
            fecha_fin = serializer.validated_data["fecha_fin"]

            # Validar que la fecha de inicio sea menor a la fecha de fin
            if fecha_inicio >= fecha_fin:
                return Response(
                    {"details": "La fecha de inicio debe ser menor que la fecha de fin"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            estado = serializer.validated_data.get("estado", "INACTIVO")

            # Si se marca como ACTIVO, desactiva otros períodos
            if estado == "ACTIVO":
                PeriodoAcademico.objects.filter(estado="ACTIVO").update(estado="INACTIVO")

            periodo = serializer.save()
            return Response({"periodo_created_id": periodo.id}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PeriodosViewEdit(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Actualiza la información de un período académico
    @transaction.atomic
    def put(self, request, *args, **kwargs):
        periodo = get_object_or_404(PeriodoAcademico, id=request.data.get("id"))

        serializer = PeriodoAcademicoSerializer(periodo, data=request.data, partial=True)

        if serializer.is_valid():
            # Usar los valores nuevos si vienen, o conservar los actuales
            fecha_inicio = serializer.validated_data.get("fecha_inicio", periodo.fecha_inicio)
            fecha_fin = serializer.validated_data.get("fecha_fin", periodo.fecha_fin)

            # Validar que la fecha de inicio sea menor a la fecha de fin
            if fecha_inicio >= fecha_fin:
                return Response(
                    {"details": "La fecha de inicio debe ser menor que la fecha de fin"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            nuevo_estado = serializer.validated_data.get("estado", periodo.estado)

            # Si se marca como ACTIVO, desactiva otros períodos
            if nuevo_estado == "ACTIVO":
                PeriodoAcademico.objects.exclude(id=periodo.id).filter(estado="ACTIVO").update(estado="INACTIVO")

            periodo = serializer.save()
            data = PeriodoAcademicoSerializer(periodo, many=False).data
            return Response(data, 200)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Elimina el período académico por id
    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        periodo = get_object_or_404(PeriodoAcademico, id=request.GET.get("id"))
        try:
            periodo.delete()
            return Response({"details": "Periodo eliminado"}, 200)
        except Exception:
            return Response({"details": "Algo pasó al eliminar el periodo"}, 400)


class PeriodoActivoView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = (permissions.AllowAny,)

    # Devuelve el período académico activo (si existe)
    def get(self, request, *args, **kwargs):
        periodo = (
            PeriodoAcademico.objects.filter(estado="ACTIVO")
            .order_by("-fecha_inicio", "-id")
            .first()
        )

        if not periodo:
            return Response({}, 200)

        data = PeriodoAcademicoSerializer(periodo, many=False).data
        return Response(data, 200)


class PeriodoSetActivoView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Marca un período como ACTIVO y desactiva los demás
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        periodo = get_object_or_404(PeriodoAcademico, id=request.data.get("id"))

        PeriodoAcademico.objects.exclude(id=periodo.id).filter(estado="ACTIVO").update(estado="INACTIVO")
        periodo.estado = "ACTIVO"
        periodo.save()

        data = PeriodoAcademicoSerializer(periodo, many=False).data
        return Response(data, 200)
