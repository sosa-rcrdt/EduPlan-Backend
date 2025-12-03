from django.shortcuts import get_object_or_404
from django.db.models import *
from django.db import transaction

from rest_framework.generics import CreateAPIView
from rest_framework import permissions, generics, status
from rest_framework.response import Response

from eduplan_api.serializers import *
from eduplan_api.models import *


class InscripcionesAll(generics.CreateAPIView):
    """
    Lista de inscripciones con filtros opcionales:
    - alumno_id
    - grupo_id
    - periodo_id
    - estado
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        inscripciones = Inscripcion.objects.all().order_by(
            "periodo__fecha_inicio", "grupo__materia__nombre", "grupo__nombre"
        )

        alumno_id = request.GET.get("alumno_id")
        if alumno_id:
            inscripciones = inscripciones.filter(alumno_id=alumno_id)

        grupo_id = request.GET.get("grupo_id")
        if grupo_id:
            inscripciones = inscripciones.filter(grupo_id=grupo_id)

        periodo_id = request.GET.get("periodo_id")
        if periodo_id:
            inscripciones = inscripciones.filter(periodo_id=periodo_id)

        estado = request.GET.get("estado")
        if estado:
            inscripciones = inscripciones.filter(estado=estado)

        lista = InscripcionSerializer(inscripciones, many=True).data
        return Response(lista, 200)


class InscripcionView(generics.CreateAPIView):
    """
    GET: Obtiene una inscripción por id.
    POST: Crea una nueva inscripción con todas las validaciones de negocio:
        - Periodo ACTIVO
        - Cupo del grupo (cupo_maximo)
        - Máx. 6 materias activas por alumno en un mismo periodo
        - No duplicar materia en el mismo periodo
        - (Opcional) No choques de horario con otros grupos del alumno
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get_rol_usuario(self, user):
        roles = list(user.groups.values_list("name", flat=True))
        return roles[0] if roles else None

    def get(self, request, *args, **kwargs):
        inscripcion = get_object_or_404(Inscripcion, id=request.GET.get("id"))
        data = InscripcionSerializer(inscripcion, many=False).data
        return Response(data, 200)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        user = request.user
        rol = self.get_rol_usuario(user)

        data = request.data.copy()

        # Si el que crea es alumno, forzamos que solo pueda inscribirse a sí mismo
        if rol == "alumno":
            alumno = Alumnos.objects.filter(user=user).first()
            if not alumno:
                return Response(
                    {"details": "El usuario autenticado no tiene perfil de alumno"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            data["alumno"] = alumno.id

        # Si es admin/maestro u otro, debe indicar explícitamente el alumno
        alumno_id = data.get("alumno")
        if not alumno_id:
            return Response(
                {"details": "Debe indicar el alumno a inscribir"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validación inicial con serializer
        serializer = InscripcionSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        alumno = serializer.validated_data["alumno"]
        grupo = serializer.validated_data["grupo"]
        periodo = serializer.validated_data["periodo"]

        # Validar que el periodo esté ACTIVO
        if periodo.estado != "ACTIVO":
            return Response(
                {
                    "details": "Solo se permiten inscripciones en un periodo ACTIVO",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Evitar duplicar inscripción mismo alumno+grupo+periodo
        if Inscripcion.objects.filter(
            alumno=alumno, grupo=grupo, periodo=periodo
        ).exists():
            return Response(
                {
                    "details": "El alumno ya está inscrito en este grupo para este periodo",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Cupo actual del grupo (inscripciones ACTIVAS)
        cupo_actual = Inscripcion.objects.filter(
            grupo=grupo,
            periodo=periodo,
            estado="ACTIVA",
        ).count()

        if cupo_actual >= grupo.cupo_maximo:
            return Response(
                {
                    "details": "El grupo ya alcanzó su cupo máximo",
                    "cupo_maximo": grupo.cupo_maximo,
                    "cupo_actual": cupo_actual,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Inscripciones activas del alumno en ese periodo
        inscripciones_activas = Inscripcion.objects.filter(
            alumno=alumno,
            periodo=periodo,
            estado="ACTIVA",
        ).select_related("grupo__materia")

        # Máx. 6 materias
        if inscripciones_activas.count() >= 6:
            return Response(
                {
                    "details": "El alumno ya tiene el máximo de 6 materias activas en este periodo",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # No duplicar materia en el mismo periodo (aunque sea en otro grupo)
        materia_del_grupo = grupo.materia
        if inscripciones_activas.filter(grupo__materia=materia_del_grupo).exists():
            return Response(
                {
                    "details": "El alumno ya está inscrito en un grupo de esta misma materia en este periodo",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar choques de horario entre el nuevo grupo y los grupos actuales del alumno
        grupos_actuales_ids = list(
            inscripciones_activas.values_list("grupo_id", flat=True)
        )

        horarios_nuevo = Horario.objects.filter(
            periodo=periodo,
            grupo=grupo,
            estado="ACTIVO",
        )

        if horarios_nuevo.exists() and grupos_actuales_ids:
            horarios_existentes = Horario.objects.filter(
                periodo=periodo,
                grupo_id__in=grupos_actuales_ids,
                estado="ACTIVO",
            )

            for h in horarios_nuevo:
                choque = horarios_existentes.filter(
                    dia_semana=h.dia_semana,
                    hora_inicio__lt=h.hora_fin,
                    hora_fin__gt=h.hora_inicio,
                ).first()

                if choque:
                    return Response(
                        {
                            "details": "El horario de este grupo se empalma con otro grupo ya inscrito por el alumno",
                            "grupo_conflictivo_id": choque.grupo_id,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        # Si todo está bien, guardamos
        inscripcion = serializer.save()
        data_resp = InscripcionSerializer(inscripcion, many=False).data
        return Response(data_resp, status=status.HTTP_201_CREATED)


class InscripcionesViewEdit(generics.CreateAPIView):
    """
    PUT: Actualiza una inscripción (típicamente estado: ACTIVA / BAJA).
         Si el estado resultante es ACTIVA, se vuelven a validar:
         - Periodo ACTIVO
         - Cupo
         - Máx. 6 materias
         - No duplicar materia
         - Choques de horario
    DELETE: Elimina la inscripción (baja definitiva).
    """
    permission_classes = (permissions.IsAuthenticated,)

    @transaction.atomic
    def put(self, request, *args, **kwargs):
        inscripcion = get_object_or_404(Inscripcion, id=request.data.get("id"))
        serializer = InscripcionSerializer(
            inscripcion, data=request.data, partial=True
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Valores actuales o nuevos
        alumno = serializer.validated_data.get("alumno", inscripcion.alumno)
        grupo = serializer.validated_data.get("grupo", inscripcion.grupo)
        periodo = serializer.validated_data.get("periodo", inscripcion.periodo)
        estado_nuevo = serializer.validated_data.get("estado", inscripcion.estado)

        # Si pasamos a ACTIVA, validamos todo de nuevo
        if estado_nuevo == "ACTIVA":
            if periodo.estado != "ACTIVO":
                return Response(
                    {
                        "details": "Solo se permiten inscripciones activas en un periodo ACTIVO",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Verificar duplicado de alumno+grupo+periodo (excluyendo la propia inscripción)
            if Inscripcion.objects.filter(
                alumno=alumno,
                grupo=grupo,
                periodo=periodo,
            ).exclude(id=inscripcion.id).exists():
                return Response(
                    {
                        "details": "Ya existe otra inscripción del alumno en este grupo para este periodo",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Cupo actual del grupo (ACTIVAS, excluyendo la propia inscripción)
            cupo_actual = Inscripcion.objects.filter(
                grupo=grupo,
                periodo=periodo,
                estado="ACTIVA",
            ).exclude(id=inscripcion.id).count()

            if cupo_actual >= grupo.cupo_maximo:
                return Response(
                    {
                        "details": "El grupo ya alcanzó su cupo máximo",
                        "cupo_maximo": grupo.cupo_maximo,
                        "cupo_actual": cupo_actual,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Inscripciones activas del alumno en ese periodo (excluyendo la propia)
            inscripciones_activas = Inscripcion.objects.filter(
                alumno=alumno,
                periodo=periodo,
                estado="ACTIVA",
            ).exclude(id=inscripcion.id).select_related("grupo__materia")

            if inscripciones_activas.count() >= 6:
                return Response(
                    {
                        "details": "El alumno ya tiene el máximo de 6 materias activas en este periodo",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # No duplicar materia en el mismo periodo
            materia_del_grupo = grupo.materia
            if inscripciones_activas.filter(
                grupo__materia=materia_del_grupo
            ).exists():
                return Response(
                    {
                        "details": "El alumno ya está inscrito en un grupo de esta misma materia en este periodo",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Choques de horario
            grupos_actuales_ids = list(
                inscripciones_activas.values_list("grupo_id", flat=True)
            )

            horarios_nuevo = Horario.objects.filter(
                periodo=periodo,
                grupo=grupo,
                estado="ACTIVO",
            )

            if horarios_nuevo.exists() and grupos_actuales_ids:
                horarios_existentes = Horario.objects.filter(
                    periodo=periodo,
                    grupo_id__in=grupos_actuales_ids,
                    estado="ACTIVO",
                )

                for h in horarios_nuevo:
                    choque = horarios_existentes.filter(
                        dia_semana=h.dia_semana,
                        hora_inicio__lt=h.hora_fin,
                        hora_fin__gt=h.hora_inicio,
                    ).first()

                    if choque:
                        return Response(
                            {
                                "details": "El horario de este grupo se empalma con otro grupo ya inscrito por el alumno",
                                "grupo_conflictivo_id": choque.grupo_id,
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

        # Guardar cambios
        inscripcion = serializer.save()
        data_resp = InscripcionSerializer(inscripcion, many=False).data
        return Response(data_resp, 200)

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        inscripcion = get_object_or_404(Inscripcion, id=request.GET.get("id"))
        try:
            inscripcion.delete()
            return Response({"details": "Inscripción eliminada"}, 200)
        except Exception:
            return Response(
                {"details": "Algo pasó al eliminar la inscripción"}, 400
            )


class InscripcionesAlumnoView(generics.GenericAPIView):
    """
    Devuelve la carga académica del alumno autenticado para un periodo:
    - Si se manda ?periodo_id=, se usa ese.
    - Si no, se toma el periodo ACTIVO más reciente.
    Respuesta: lista de inscripciones con
      - grupo
      - materia
      - periodo
      - horarios del grupo (ACTIVOS)
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        user = request.user
        alumno = Alumnos.objects.filter(user=user).first()

        if not alumno:
            return Response(
                {"details": "El usuario autenticado no tiene perfil de alumno"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        periodo_id = request.GET.get("periodo_id")
        periodo = None

        if periodo_id:
            periodo = get_object_or_404(PeriodoAcademico, id=periodo_id)
        else:
            periodo = (
                PeriodoAcademico.objects.filter(estado="ACTIVO")
                .order_by("-fecha_inicio")
                .first()
            )

        if not periodo:
            return Response(
                {"details": "No hay un periodo académico ACTIVO definido"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inscripciones = (
            Inscripcion.objects.filter(
                alumno=alumno,
                periodo=periodo,
                estado="ACTIVA",
            )
            .select_related("grupo__materia", "periodo")
            .order_by("grupo__materia__nombre", "grupo__nombre")
        )

        resultado = []
        for insc in inscripciones:
            grupo = insc.grupo
            materia = grupo.materia

            horarios = Horario.objects.filter(
                periodo=periodo,
                grupo=grupo,
                estado="ACTIVO",
            ).order_by("dia_semana", "hora_inicio")

            item = {
                "inscripcion": InscripcionSerializer(insc, many=False).data,
                "grupo": GrupoSerializer(grupo, many=False).data,
                "materia": MateriaSerializer(materia, many=False).data,
                "periodo": PeriodoAcademicoSerializer(periodo, many=False).data,
                "horarios": HorarioSerializer(horarios, many=True).data,
            }
            resultado.append(item)

        return Response(resultado, 200)
