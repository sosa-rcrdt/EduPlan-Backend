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


class AulasAll(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Devuelve el listado de aulas (permite filtrar por edificio, estado y capacidad mínima)
    def get(self, request, *args, **kwargs):
        aulas = Aula.objects.all().order_by("edificio", "numero")

        edificio = request.GET.get("edificio")
        if edificio:
            aulas = aulas.filter(edificio__icontains=edificio)

        estado = request.GET.get("estado")
        if estado:
            aulas = aulas.filter(estado=estado)

        capacidad_min = request.GET.get("capacidad_min")
        if capacidad_min:
            aulas = aulas.filter(capacidad__gte=capacidad_min)

        lista = AulaSerializer(aulas, many=True).data
        return Response(lista, 200)


class AulaView(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Obtiene la información de un aula por id
    def get(self, request, *args, **kwargs):
        aula = get_object_or_404(Aula, id=request.GET.get("id"))
        aula = AulaSerializer(aula, many=False).data
        return Response(aula, 200)

    # Registra una nueva aula
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = AulaSerializer(data=request.data)

        if serializer.is_valid():
            aula = serializer.save()
            return Response(
                {"aula_created_id": aula.id},
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AulasViewEdit(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Actualiza la información de un aula existente
    @transaction.atomic
    def put(self, request, *args, **kwargs):
        aula = get_object_or_404(Aula, id=request.data.get("id"))
        serializer = AulaSerializer(aula, data=request.data, partial=True)

        if serializer.is_valid():
            aula = serializer.save()
            data = AulaSerializer(aula, many=False).data
            return Response(data, 200)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Elimina un aula por id
    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        aula = get_object_or_404(Aula, id=request.GET.get("id"))
        try:
            aula.delete()
            return Response({"details": "Aula eliminada"}, 200)
        except Exception:
            return Response({"details": "Algo pasó al eliminar el aula"}, 400)


class AulasDisponiblesView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Devuelve las aulas disponibles para un día y franja horaria (sin choques de horario)
    def get(self, request, *args, **kwargs):
        dia_semana = request.GET.get("dia_semana")
        hora_inicio_str = request.GET.get("hora_inicio")
        hora_fin_str = request.GET.get("hora_fin")
        periodo_id = request.GET.get("periodo_id")

        # Validar parámetros obligatorios
        if dia_semana is None or hora_inicio_str is None or hora_fin_str is None:
            return Response(
                {"details": "Debe indicar dia_semana, hora_inicio y hora_fin"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            dia_semana = int(dia_semana)
        except ValueError:
            return Response(
                {"details": "dia_semana debe ser un número entero"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Se asume formato HH:MM
            hora_inicio = datetime.strptime(hora_inicio_str, "%H:%M").time()
            hora_fin = datetime.strptime(hora_fin_str, "%H:%M").time()
        except ValueError:
            return Response(
                {"details": "hora_inicio y hora_fin deben tener formato HH:MM"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if hora_inicio >= hora_fin:
            return Response(
                {"details": "hora_inicio debe ser menor que hora_fin"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Horarios ocupados en esa franja
        horarios_ocupados = Horario.objects.filter(
            dia_semana=dia_semana,
            estado="ACTIVO",
        )

        if periodo_id:
            horarios_ocupados = horarios_ocupados.filter(periodo_id=periodo_id)

        # Overlap: inicio < fin_existente y fin > inicio_existente
        horarios_ocupados = horarios_ocupados.filter(
            hora_inicio__lt=hora_fin,
            hora_fin__gt=hora_inicio,
        )

        aulas_ocupadas_ids = horarios_ocupados.values_list("aula_id", flat=True).distinct()

        aulas_disponibles = Aula.objects.filter(estado="DISPONIBLE").exclude(
            id__in=aulas_ocupadas_ids
        ).order_by("edificio", "numero")

        data = AulaSerializer(aulas_disponibles, many=True).data
        return Response(data, 200)
