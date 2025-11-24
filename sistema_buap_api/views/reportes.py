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


class ReporteUsoAulasView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Devuelve resumen de uso de aulas por periodo (horas totales y número de horarios)
    def get(self, request, *args, **kwargs):
        periodo_id = request.GET.get("periodo_id")
        aula_id = request.GET.get("aula_id")

        if not periodo_id:
            return Response(
                {"details": "Debe indicar el parámetro periodo_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        horarios = Horario.objects.filter(
            periodo_id=periodo_id,
            estado="ACTIVO",
        ).select_related("aula")

        if aula_id:
            horarios = horarios.filter(aula_id=aula_id)

        resumen = {}
        for h in horarios:
            # duración en horas como número flotante
            dur_horas = (
                (h.hora_fin.hour + h.hora_fin.minute / 60.0)
                - (h.hora_inicio.hour + h.hora_inicio.minute / 60.0)
            )
            item = resumen.get(h.aula_id)
            if not item:
                item = {
                    "aula_id": h.aula_id,
                    "aula": str(h.aula),
                    "total_horas": 0.0,
                    "num_horarios": 0,
                }
            item["total_horas"] += max(dur_horas, 0.0)
            item["num_horarios"] += 1
            resumen[h.aula_id] = item

        data = list(resumen.values())
        return Response(data, 200)

class ReporteCargaDocenteView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Devuelve la carga académica de docentes por periodo (horas totales y grupos asignados)
    def get(self, request, *args, **kwargs):
        periodo_id = request.GET.get("periodo_id")
        docente_id = request.GET.get("docente_id")

        if not periodo_id:
            return Response(
                {"details": "Debe indicar el parámetro periodo_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        horarios = Horario.objects.filter(
            periodo_id=periodo_id,
            estado="ACTIVO",
        ).select_related("docente", "docente__user", "grupo")

        if docente_id:
            horarios = horarios.filter(docente_id=docente_id)

        resumen = {}

        for h in horarios:
            # duración en horas como número flotante
            dur_horas = (
                (h.hora_fin.hour + h.hora_fin.minute / 60.0)
                - (h.hora_inicio.hour + h.hora_inicio.minute / 60.0)
            )

            key = h.docente_id

            item = resumen.get(key)
            if not item:
                # armamos el nombre a partir del User relacionado
                nombre_docente = ""
                if getattr(h.docente, "user", None):
                    nombre_docente = f"{h.docente.user.first_name} {h.docente.user.last_name}".strip()
                if not nombre_docente:
                    nombre_docente = f"Maestro {h.docente_id}"

                item = {
                    "docente_id": h.docente_id,
                    "docente": nombre_docente,
                    "total_horas": 0.0,
                    "grupos_ids": set(),
                }

            item["total_horas"] += max(dur_horas, 0.0)
            item["grupos_ids"].add(h.grupo_id)
            resumen[key] = item

        data = []
        for item in resumen.values():
            data.append(
                {
                    "docente_id": item["docente_id"],
                    "docente": item["docente"],
                    "total_horas": item["total_horas"],
                    "num_grupos": len(item["grupos_ids"]),
                }
            )

        return Response(data, 200)

class ReporteGrupoView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Devuelve información de un grupo y sus horarios en un periodo (si se indica)
    def get(self, request, *args, **kwargs):
        grupo_id = request.GET.get("grupo_id")
        periodo_id = request.GET.get("periodo_id")

        if not grupo_id:
            return Response(
                {"details": "Debe indicar el parámetro grupo_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        grupo = get_object_or_404(Grupo, id=grupo_id)
        grupo_data = GrupoSerializer(grupo, many=False).data

        horarios = Horario.objects.filter(grupo_id=grupo_id)
        if periodo_id:
            horarios = horarios.filter(periodo_id=periodo_id)

        horarios = horarios.order_by("dia_semana", "hora_inicio")
        horarios_data = HorarioSerializer(horarios, many=True).data

        data = {
            "grupo": grupo_data,
            "horarios": horarios_data,
        }
        return Response(data, 200)


class ReportePeriodoResumenView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Devuelve un resumen general del periodo (grupos, aulas, docentes, horarios y horas totales)
    def get(self, request, *args, **kwargs):
        periodo_id = request.GET.get("periodo_id")

        if not periodo_id:
            return Response(
                {"details": "Debe indicar el parámetro periodo_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        periodo = get_object_or_404(PeriodoAcademico, id=periodo_id)

        horarios = Horario.objects.filter(
            periodo_id=periodo_id,
            estado="ACTIVO",
        )

        total_horarios = horarios.count()
        total_grupos = horarios.values("grupo_id").distinct().count()
        total_aulas_usadas = horarios.values("aula_id").distinct().count()
        total_docentes = horarios.values("docente_id").distinct().count()

        total_horas = 0.0
        for h in horarios:
            dur_horas = (
                (h.hora_fin.hour + h.hora_fin.minute / 60.0)
                - (h.hora_inicio.hour + h.hora_inicio.minute / 60.0)
            )
            total_horas += max(dur_horas, 0.0)

        data = {
            "periodo_id": periodo.id,
            "periodo": str(periodo),
            "total_horarios": total_horarios,
            "total_grupos": total_grupos,
            "total_aulas_usadas": total_aulas_usadas,
            "total_docentes": total_docentes,
            "total_horas": total_horas,
        }
        return Response(data, 200)

class PublicSummaryView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = (permissions.AllowAny,)

    # Devuelve resumen público del sistema (periodo activo y algunos conteos)
    def get(self, request, *args, **kwargs):
        periodo = (
            PeriodoAcademico.objects.filter(estado="ACTIVO")
            .order_by("-fecha_inicio", "-id")
            .first()
        )

        if not periodo:
            return Response({}, 200)

        horarios = Horario.objects.filter(
            periodo=periodo,
            estado="ACTIVO",
        )

        total_grupos = horarios.values("grupo_id").distinct().count()
        total_aulas_usadas = horarios.values("aula_id").distinct().count()
        total_docentes = horarios.values("docente_id").distinct().count()
        aulas_disponibles = Aula.objects.filter(estado="DISPONIBLE").count()

        periodo_data = PeriodoAcademicoSerializer(periodo, many=False).data

        data = {
            "periodo_activo": periodo_data,
            "total_grupos_con_horario": total_grupos,
            "total_aulas_usadas": total_aulas_usadas,
            "total_docentes_con_horario": total_docentes,
            "aulas_disponibles": aulas_disponibles,
        }
        return Response(data, 200)
