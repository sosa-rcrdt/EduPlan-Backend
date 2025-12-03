from django.shortcuts import get_object_or_404
from django.db.models import *
from django.db import transaction
from django.conf import settings
from django.template.loader import render_to_string
from django.core import serializers
from django.utils.html import strip_tags
from django.utils import timezone

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
        dia_semana = request.data.get("dia_semana_propuesto")
        hora_inicio = request.data.get("hora_inicio_propuesta")
        hora_fin = request.data.get("hora_fin_propuesta")
        motivo = request.data.get("motivo")

        if not grupo_id:
            return Response(
                {"details": "Debe indicar el grupo para la solicitud."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if dia_semana is None or hora_inicio is None or hora_fin is None:
            return Response(
                {
                    "details": "Debe indicar día de la semana, hora de inicio y hora de fin propuestos."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar que el maestro realmente imparte ese grupo en algún horario
        imparte_grupo = Horario.objects.filter(
            grupo_id=grupo_id,
            docente=maestro,
            estado="ACTIVO",
        ).exists()

        if not imparte_grupo:
            return Response(
                {
                    "details": "El docente autenticado no tiene horarios activos asignados para este grupo."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = {
            "docente": maestro.id,
            "grupo": grupo_id,
            "dia_semana_propuesto": dia_semana,
            "hora_inicio_propuesta": hora_inicio,
            "hora_fin_propuesta": hora_fin,
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

    # Aprueba una solicitud de cambio y aplica el cambio de horario
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        solicitud_id = request.data.get("id")
        if not solicitud_id:
            return Response(
                {"details": "Debe indicar el id de la solicitud a aprobar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        solicitud = get_object_or_404(SolicitudCambio, id=solicitud_id)

        if solicitud.estado != "PENDIENTE":
            return Response(
                {"details": "La solicitud ya fue procesada previamente."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dia_nuevo = solicitud.dia_semana_propuesto
        hora_inicio_nueva = solicitud.hora_inicio_propuesta
        hora_fin_nueva = solicitud.hora_fin_propuesta

        # Validación básica de horas (por si algo cambió desde el serializer)
        if hora_inicio_nueva >= hora_fin_nueva:
            return Response(
                {
                    "details": "La hora de inicio propuesta debe ser menor que la hora de fin."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Buscar horarios activos de ese grupo y docente
        horarios = Horario.objects.filter(
            grupo=solicitud.grupo,
            docente=solicitud.docente,
            estado="ACTIVO",
        )

        if not horarios.exists():
            return Response(
                {
                    "details": "No se encontraron horarios activos para el grupo y docente de la solicitud."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar posibles choques para cada horario antes de aplicar
        for horario in horarios:
            periodo = horario.periodo
            aula = horario.aula
            docente = horario.docente

            # Validar que el periodo esté ACTIVO
            if periodo.estado != "ACTIVO":
                return Response(
                    {
                        "details": "Solo se pueden modificar horarios de un periodo ACTIVO."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validar choques de aula
            choques_aula = Horario.objects.filter(
                periodo=periodo,
                aula=aula,
                dia_semana=dia_nuevo,
                estado="ACTIVO",
                hora_inicio__lt=hora_fin_nueva,
                hora_fin__gt=hora_inicio_nueva,
            ).exclude(id=horario.id)

            if choques_aula.exists():
                return Response(
                    {
                        "details": "El aula ya está ocupada en la franja horaria propuesta.",
                        "horario_conflictivo_id": choques_aula.first().id,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validar choques de docente
            choques_docente = Horario.objects.filter(
                periodo=periodo,
                docente=docente,
                dia_semana=dia_nuevo,
                estado="ACTIVO",
                hora_inicio__lt=hora_fin_nueva,
                hora_fin__gt=hora_inicio_nueva,
            ).exclude(id=horario.id)

            if choques_docente.exists():
                return Response(
                    {
                        "details": "El docente ya tiene un horario en la franja horaria propuesta.",
                        "horario_conflictivo_id": choques_docente.first().id,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Si todas las validaciones pasan, aplicamos el cambio a todos los horarios del grupo/docente
        for horario in horarios:
            horario.dia_semana = dia_nuevo
            horario.hora_inicio = hora_inicio_nueva
            horario.hora_fin = hora_fin_nueva
            horario.save()

        solicitud.estado = "APROBADA"
        solicitud.fecha_resolucion = timezone.now()
        solicitud.save()

        data = SolicitudCambioSerializer(solicitud, many=False).data
        return Response(data, 200)


class SolicitudRejectView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Rechaza una solicitud de cambio y registra la fecha de resolución
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        solicitud_id = request.data.get("id")
        if not solicitud_id:
            return Response(
                {"details": "Debe indicar el id de la solicitud a rechazar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        solicitud = get_object_or_404(SolicitudCambio, id=solicitud_id)

        if solicitud.estado != "PENDIENTE":
            return Response(
                {"details": "La solicitud ya fue procesada previamente."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        solicitud.estado = "RECHAZADA"
        solicitud.fecha_resolucion = timezone.now()
        solicitud.save()

        data = SolicitudCambioSerializer(solicitud, many=False).data
        return Response(data, 200)
