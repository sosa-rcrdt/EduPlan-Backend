from django.contrib import admin
from django.urls import path

from rest_framework_simplejwt.views import TokenRefreshView

from eduplan_api.views import bootstrap
from eduplan_api.views import users
from eduplan_api.views import alumnos
from eduplan_api.views import maestros
from eduplan_api.views import auth
from eduplan_api.views import periodos
from eduplan_api.views import materias
from eduplan_api.views import grupos
from eduplan_api.views import aulas
from eduplan_api.views import horarios
from eduplan_api.views import solicitudes
from eduplan_api.views import reportes
from eduplan_api.views import inscripciones
from eduplan_api.views import notificaciones


urlpatterns = [
    # Admins
    path('admin/', users.AdminView.as_view()),             # GET por id / POST crear admin + user
    path('lista-admins/', users.AdminAll.as_view()),       # GET lista de admins
    path('admins-edit/', users.AdminsViewEdit.as_view()),  # GET conteos / PUT / DELETE admin

    # Alumnos
    path('alumnos/', alumnos.AlumnosView.as_view()),          # GET por id / POST crear alumno + user
    path('lista-alumnos/', alumnos.AlumnosAll.as_view()),     # GET lista alumnos
    path('alumnos-edit/', alumnos.AlumnosViewEdit.as_view()), # PUT / DELETE alumno

    # Maestros
    path('maestros/', maestros.MaestrosView.as_view()),          # GET por id / POST crear maestro + user
    path('lista-maestros/', maestros.MaestrosAll.as_view()),     # GET lista maestros
    path('maestros-edit/', maestros.MaestrosViewEdit.as_view()), # PUT / DELETE maestro

    # Perfil del usuario logueado (admin / alumno / maestro)
    path('profile/me/', users.ProfileView.as_view()),

    # Auth (JWT)
    path('token/', auth.LoginJWTView.as_view(), name='token_obtain_pair'),  # Login JWT (access + refresh + rol + perfil)
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Refresh access token
    path('logout/', auth.Logout.as_view()),                      # Logout lógico (frontend borra token)
    path('change-password/', auth.ChangePasswordView.as_view()), # Cambiar contraseña

    # Periodos
    path('periodos/', periodos.PeriodosAll.as_view()),           # GET lista periodos
    path('periodo/', periodos.PeriodoView.as_view()),            # GET por id / POST crear periodo
    path('periodos-edit/', periodos.PeriodosViewEdit.as_view()), # PUT / DELETE periodo
    path('periodo-activo/', periodos.PeriodoActivoView.as_view()),      # GET periodo activo (público)
    path('periodo-set-activo/', periodos.PeriodoSetActivoView.as_view()),  # POST marcar periodo activo

    # Materias
    path('materias/', materias.MateriasAll.as_view()),           # GET lista materias (filtros)
    path('materia/', materias.MateriaView.as_view()),            # GET por id / POST crear materia
    path('materias-edit/', materias.MateriasViewEdit.as_view()), # PUT / DELETE materia

    # Grupos
    path('grupos/', grupos.GruposAll.as_view()),           # GET lista grupos (filtros)
    path('grupo/', grupos.GrupoView.as_view()),            # GET por id / POST crear grupo
    path('grupos-edit/', grupos.GruposViewEdit.as_view()), # PUT / DELETE grupo
    path('grupo-horarios/', grupos.GrupoHorariosView.as_view()), # GET horarios de un grupo

    # Aulas
    path('aulas/', aulas.AulasAll.as_view()),              # GET lista aulas (filtros)
    path('aula/', aulas.AulaView.as_view()),               # GET por id / POST crear aula
    path('aulas-edit/', aulas.AulasViewEdit.as_view()),    # PUT / DELETE aula
    path('aulas-disponibles/', aulas.AulasDisponiblesView.as_view()), # GET aulas libres para franja

    # Horarios
    path('horarios/', horarios.HorariosAll.as_view()),        # GET lista / POST crear horario
    path('horario/', horarios.HorarioView.as_view()),         # GET por id / PUT / DELETE horario
    path('horarios-docente/', horarios.HorariosDocenteView.as_view()), # GET horarios del docente logueado

    # Solicitudes
    path('solicitudes/', solicitudes.SolicitudesAll.as_view()),          # GET lista solicitudes (admin)
    path('solicitud/', solicitudes.SolicitudView.as_view()),             # GET por id / POST crear (docente)
    path('solicitudes-edit/', solicitudes.SolicitudesViewEdit.as_view()),# PUT / DELETE solicitud
    path('solicitudes-docente/', solicitudes.SolicitudesDocenteView.as_view()), # GET solicitudes del docente logueado
    path('solicitud-aprobar/', solicitudes.SolicitudApproveView.as_view()),     # POST aprobar solicitud
    path('solicitud-rechazar/', solicitudes.SolicitudRejectView.as_view()),     # POST rechazar solicitud

    # Reportes
    path('reporte-uso-aulas/', reportes.ReporteUsoAulasView.as_view()),           # GET uso de aulas
    path('reporte-carga-docente/', reportes.ReporteCargaDocenteView.as_view()),   # GET carga por docente
    path('reporte-grupo/', reportes.ReporteGrupoView.as_view()),                  # GET info grupo + horarios
    path('reporte-periodo-resumen/', reportes.ReportePeriodoResumenView.as_view()), # GET resumen general periodo

    # Resumen público para landing / home
    path('public/summary/', reportes.PublicSummaryView.as_view()),

    # Inscripciones (Alumno–Grupo–Periodo)
    path('inscripciones/', inscripciones.InscripcionesAll.as_view()),              # GET lista inscripciones (filtros)
    path('inscripcion/', inscripciones.InscripcionView.as_view()),                 # GET por id / POST crear inscripción
    path('inscripciones-edit/', inscripciones.InscripcionesViewEdit.as_view()),    # PUT / DELETE inscripción
    path('inscripciones-alumno/', inscripciones.InscripcionesAlumnoView.as_view()),# GET carga académica del alumno logueado

    # Notificaciones
    path('notificaciones/', notificaciones.NotificacionesView.as_view()),
]
