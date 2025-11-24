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

from sistema_buap_api.serializers import *
from sistema_buap_api.models import *


class MateriasAll(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Devuelve el listado de materias (permite filtrar por área y búsqueda)
    def get(self, request, *args, **kwargs):
        materias = Materia.objects.all().order_by("nombre")

        # Filtro opcional por área académica
        area_academica = request.GET.get("area_academica")
        if area_academica:
            materias = materias.filter(area_academica__icontains=area_academica)

        # Búsqueda opcional por nombre o código
        search = request.GET.get("search")
        if search:
            materias = materias.filter(
                Q(nombre__icontains=search) | Q(codigo__icontains=search)
            )

        lista = MateriaSerializer(materias, many=True).data
        return Response(lista, 200)


class MateriaView(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Obtiene la información de una materia por id
    def get(self, request, *args, **kwargs):
        materia = get_object_or_404(Materia, id=request.GET.get("id"))
        materia = MateriaSerializer(materia, many=False).data
        return Response(materia, 200)

    # Registra una nueva materia
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = MateriaSerializer(data=request.data)

        if serializer.is_valid():
            # El modelo ya valida unicidad de código
            materia = serializer.save()
            return Response(
                {"materia_created_id": materia.id},
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MateriasViewEdit(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Actualiza la información de una materia existente
    @transaction.atomic
    def put(self, request, *args, **kwargs):
        materia = get_object_or_404(Materia, id=request.data.get("id"))
        serializer = MateriaSerializer(materia, data=request.data, partial=True)

        if serializer.is_valid():
            materia = serializer.save()
            data = MateriaSerializer(materia, many=False).data
            return Response(data, 200)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Elimina una materia por id
    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        materia = get_object_or_404(Materia, id=request.GET.get("id"))
        try:
            materia.delete()
            return Response({"details": "Materia eliminado"}, 200)
        except Exception:
            return Response({"details": "Algo pasó al eliminar la materia"}, 400)
