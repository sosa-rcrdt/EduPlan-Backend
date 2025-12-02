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


class GruposAll(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Devuelve el listado de grupos (permite filtros por materia, semestre y búsqueda)
    def get(self, request, *args, **kwargs):
        grupos = Grupo.objects.all().order_by("semestre", "nombre")

        materia_id = request.GET.get("materia_id")
        if materia_id:
            grupos = grupos.filter(materia_id=materia_id)

        semestre = request.GET.get("semestre")
        if semestre:
            grupos = grupos.filter(semestre=semestre)

        search = request.GET.get("search")
        if search:
            grupos = grupos.filter(
                Q(nombre__icontains=search)
                | Q(materia__nombre__icontains=search)
                | Q(materia__codigo__icontains=search)
            )

        lista = GrupoSerializer(grupos, many=True).data
        return Response(lista, 200)


class GrupoView(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Obtiene la información de un grupo por id
    def get(self, request, *args, **kwargs):
        grupo = get_object_or_404(Grupo, id=request.GET.get("id"))
        grupo = GrupoSerializer(grupo, many=False).data
        return Response(grupo, 200)

    # Registra un nuevo grupo
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = GrupoSerializer(data=request.data)

        if serializer.is_valid():
            grupo = serializer.save()
            return Response(
                {"grupo_created_id": grupo.id},
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GruposViewEdit(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Actualiza la información de un grupo existente
    @transaction.atomic
    def put(self, request, *args, **kwargs):
        grupo = get_object_or_404(Grupo, id=request.data.get("id"))
        serializer = GrupoSerializer(grupo, data=request.data, partial=True)

        if serializer.is_valid():
            grupo = serializer.save()
            data = GrupoSerializer(grupo, many=False).data
            return Response(data, 200)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Elimina un grupo por id
    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        grupo = get_object_or_404(Grupo, id=request.GET.get("id"))
        try:
            grupo.delete()
            return Response({"details": "Grupo eliminado"}, 200)
        except Exception:
            return Response({"details": "Algo pasó al eliminar el grupo"}, 400)


class GrupoHorariosView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Devuelve los horarios asociados a un grupo
    def get(self, request, *args, **kwargs):
        grupo_id = request.GET.get("grupo_id")
        if not grupo_id:
            return Response(
                {"details": "Debe indicar el parámetro grupo_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        horarios = Horario.objects.filter(grupo_id=grupo_id).order_by(
            "dia_semana", "hora_inicio"
        )
        data = HorarioSerializer(horarios, many=True).data
        return Response(data, 200)
