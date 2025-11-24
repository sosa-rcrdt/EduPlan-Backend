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


class SolicitudesAll(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Devuelve el listado de solicitudes de cambio (permite filtrar por estado, grupo y docente)
    def get(self, request, *args, **kwargs):
        solicitudes = SolicitudCambio.objects.all().order_by("-fecha_creacion")

        estado = request.GET.get("estado")
        if estado:
            solicitudes = solicitudes.filter(estado=estado)

        grupo_id = request.GET.get("grupo_id")
        if grupo_id:
            solicitudes = solicitudes.filter(grupo_id=grupo_id)

        docente_id = request.GET.get("docente_id")
        if docente_id:
            solicitudes = solicitudes.filter(docente_id=docente_id)

        data = SolicitudCambioSerializer(solicitudes, many=True).data
        return Response(data, 200)


class SolicitudView(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Obtiene la información de una solicitud por id
    def get(self, request, *args, **kwargs):
        solicitud = get_object_or_404(SolicitudCambio, id=request.GET.get("id"))
        data = SolicitudCambioSerializer(solicitud, many=False).data
        return Response(data, 200)

    # Crea una nueva solicitud de cambio para el docente autenticado
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        maestro = Maestros.objects.filter(user=request.user).first()
        if not maestro:
            return Response(
                {"details": "El usuario autenticado no tiene perfil de maestro"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        grupo_id = request.data.get("grupo")
        fecha_propuesta = request.data.get("fecha_propuesta")
        motivo = request.data.get("motivo")

        payload = {
            "docente": maestro.id,
            "grupo": grupo_id,
            "fecha_propuesta": fecha_propuesta,
            "motivo": motivo,
            "estado": "PENDIENTE",  # siempre inicia como pendiente
        }

        serializer = SolicitudCambioSerializer(data=payload)

        if serializer.is_valid():
            solicitud = serializer.save()
            return Response(
                {"solicitud_created_id": solicitud.id},
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SolicitudesViewEdit(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Actualiza la información de una solicitud (pensado para ajustes desde administración)
    @transaction.atomic
    def put(self, request, *args, **kwargs):
        solicitud = get_object_or_404(SolicitudCambio, id=request.data.get("id"))
        serializer = SolicitudCambioSerializer(
            solicitud, data=request.data, partial=True
        )

        if serializer.is_valid():
            solicitud = serializer.save()
            data = SolicitudCambioSerializer(solicitud, many=False).data
            return Response(data, 200)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Elimina una solicitud de cambio por id
    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        solicitud = get_object_or_404(SolicitudCambio, id=request.GET.get("id"))
        try:
            solicitud.delete()
            return Response({"details": "Solicitud eliminada"}, 200)
        except Exception:
            return Response({"details": "Algo pasó al eliminar la solicitud"}, 400)


class SolicitudesDocenteView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Devuelve las solicitudes de cambio del docente autenticado (permite filtrar por estado)
    def get(self, request, *args, **kwargs):
        maestro = Maestros.objects.filter(user=request.user).first()
        if not maestro:
            return Response(
                {"details": "El usuario autenticado no tiene perfil de maestro"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        solicitudes = SolicitudCambio.objects.filter(docente=maestro).order_by(
            "-fecha_creacion"
        )

        estado = request.GET.get("estado")
        if estado:
            solicitudes = solicitudes.filter(estado=estado)

        data = SolicitudCambioSerializer(solicitudes, many=True).data
        return Response(data, 200)


class SolicitudApproveView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Aprueba una solicitud de cambio y registra la fecha de resolución
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        solicitud = get_object_or_404(SolicitudCambio, id=request.data.get("id"))

        solicitud.estado = "APROBADA"
        solicitud.fecha_resolucion = datetime.now()
        solicitud.save()

        data = SolicitudCambioSerializer(solicitud, many=False).data
        return Response(data, 200)


class SolicitudRejectView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Rechaza una solicitud de cambio y registra la fecha de resolución
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        solicitud = get_object_or_404(SolicitudCambio, id=request.data.get("id"))

        solicitud.estado = "RECHAZADA"
        solicitud.fecha_resolucion = datetime.now()
        solicitud.save()

        data = SolicitudCambioSerializer(solicitud, many=False).data
        return Response(data, 200)
