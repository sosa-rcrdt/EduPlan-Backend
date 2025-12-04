from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authentication import TokenAuthentication
from django.contrib.auth.models import AbstractUser, User
from django.conf import settings

from django.db import models
from django.contrib.auth.models import User

from rest_framework.authentication import TokenAuthentication

class BearerTokenAuthentication(TokenAuthentication):
    keyword = "Bearer"


class Administradores(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False, default=None)
    clave_admin = models.CharField(max_length=255,null=True, blank=True)
    telefono = models.CharField(max_length=255, null=True, blank=True)
    rfc = models.CharField(max_length=255,null=True, blank=True)
    edad = models.IntegerField(null=True, blank=True)
    ocupacion = models.CharField(max_length=255,null=True, blank=True)
    creation = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    update = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return "Perfil Del Administrador: "+self.first_name+" "+self.last_name

class Alumnos(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False, default=None)
    matricula = models.CharField(max_length=255,null=True, blank=True)
    curp = models.CharField(max_length=255,null=True, blank=True)
    rfc = models.CharField(max_length=255,null=True, blank=True)
    fecha_nacimiento = models.DateTimeField(auto_now_add=False, null=True, blank=True)
    edad = models.IntegerField(null=True, blank=True)
    telefono = models.CharField(max_length=255, null=True, blank=True)
    ocupacion = models.CharField(max_length=255,null=True, blank=True)
    creation = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    update = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return "Perfil del alumno "+self.first_name+" "+self.last_name

class Maestros(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False, default=None)
    id_trabajador = models.CharField(max_length=255,null=True, blank=True)
    fecha_nacimiento = models.DateTimeField(auto_now_add=False, null=True, blank=True)
    telefono = models.CharField(max_length=255, null=True, blank=True)
    rfc = models.CharField(max_length=255,null=True, blank=True)
    cubiculo = models.CharField(max_length=255,null=True, blank=True)
    edad = models.IntegerField(null=True, blank=True)
    area_investigacion = models.CharField(max_length=255,null=True, blank=True)
    materias_json = models.TextField(null=True, blank=True)
    creation = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    update = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return "Perfil del maestro "+self.first_name+" "+self.last_name

class PeriodoAcademico(models.Model):
    ESTADO_CHOICES = (
        ("ACTIVO", "Activo"),
        ("INACTIVO", "Inactivo"),
    )

    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(
        max_length=10, choices=ESTADO_CHOICES, default="INACTIVO"
    )

    creation = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    update = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "Periodo académico"
        verbose_name_plural = "Periodos académicos"

    def __str__(self):
        return f"{self.nombre} ({self.estado})"


class Materia(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=150)
    codigo = models.CharField(max_length=50, unique=True)
    creditos = models.PositiveSmallIntegerField()
    area_academica = models.CharField(max_length=150)

    creation = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    update = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "Materia"
        verbose_name_plural = "Materias"

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Grupo(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=50)  # Ej. "2A", "3B"
    semestre = models.PositiveSmallIntegerField()
    materia = models.ForeignKey(Materia, on_delete=models.PROTECT, related_name="grupos")
    cupo_maximo = models.PositiveIntegerField()

    creation = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    update = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "Grupo"
        verbose_name_plural = "Grupos"

    def __str__(self):
        return f"{self.nombre} - {self.materia}"


class Aula(models.Model):
    ESTADO_CHOICES = (
        ("DISPONIBLE", "Disponible"),
        ("NO_DISPONIBLE", "No disponible"),
    )

    id = models.BigAutoField(primary_key=True)
    edificio = models.CharField(max_length=100)
    numero = models.CharField(max_length=50)
    capacidad = models.PositiveIntegerField()
    recursos = models.TextField(blank=True, null=True)  # proyector, clima, etc.
    estado = models.CharField(
        max_length=15, choices=ESTADO_CHOICES, default="DISPONIBLE"
    )

    creation = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    update = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "Aula"
        verbose_name_plural = "Aulas"
        unique_together = ("edificio", "numero")

    def __str__(self):
        return f"{self.edificio} {self.numero}"


class Horario(models.Model):
    ESTADO_CHOICES = (
        ("ACTIVO", "Activo"),
        ("CANCELADO", "Cancelado"),
    )

    DIA_CHOICES = (
        (0, "Lunes"),
        (1, "Martes"),
        (2, "Miércoles"),
        (3, "Jueves"),
        (4, "Viernes"),
        (5, "Sábado"),
    )

    id = models.BigAutoField(primary_key=True)
    periodo = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.PROTECT,
        related_name="horarios",
        help_text="Periodo académico al que pertenece el horario",
    )
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, related_name="horarios")
    aula = models.ForeignKey(Aula, on_delete=models.PROTECT, related_name="horarios")
    dia_semana = models.IntegerField(choices=DIA_CHOICES)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    docente = models.ForeignKey(
        Maestros, on_delete=models.PROTECT, related_name="horarios"
    )
    estado = models.CharField(
        max_length=10, choices=ESTADO_CHOICES, default="ACTIVO"
    )

    creation = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    update = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "Horario"
        verbose_name_plural = "Horarios"
        # Evitar choques simples por aula/docente en misma franja
        indexes = [
            models.Index(fields=["aula", "dia_semana", "hora_inicio", "hora_fin"]),
            models.Index(fields=["docente", "dia_semana", "hora_inicio", "hora_fin"]),
        ]

    def __str__(self):
        return f"{self.grupo} - {self.get_dia_semana_display()} {self.hora_inicio}-{self.hora_fin}"

class SolicitudCambio(models.Model):
    ESTADO_CHOICES = (
        ("PENDIENTE", "Pendiente"),
        ("APROBADA", "Aprobada"),
        ("RECHAZADA", "Rechazada"),
    )

    id = models.BigAutoField(primary_key=True)

    docente = models.ForeignKey(
        Maestros,
        on_delete=models.CASCADE,
        related_name="solicitudes_cambio",
    )

    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.CASCADE,
        related_name="solicitudes_cambio",
    )

    dia_semana_original = models.IntegerField(
        choices=Horario.DIA_CHOICES,
        default=0,  # Lunes por defecto para registros existentes
        help_text="Día de la semana que se desea cambiar",
    )

    dia_semana_propuesto = models.IntegerField(
        choices=Horario.DIA_CHOICES,
        null=True,
        blank=True,
        help_text="Día de la semana propuesto para el nuevo horario",
    )
    hora_inicio_propuesta = models.TimeField(
        null=True,
        blank=True,
        help_text="Hora de inicio propuesta para el nuevo horario",
    )
    hora_fin_propuesta = models.TimeField(
        null=True,
        blank=True,
        help_text="Hora de fin propuesta para el nuevo horario",
    )

    motivo = models.TextField()

    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default="PENDIENTE",
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

    creation = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    update = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "Solicitud de cambio"
        verbose_name_plural = "Solicitudes de cambio"

    def __str__(self):
        return f"Solicitud {self.id} - {self.docente} - {self.grupo} ({self.estado})"

class Inscripcion(models.Model):
    ESTADO_CHOICES = (
        ("ACTIVA", "Activa"),
        ("BAJA", "Baja"),
    )

    id = models.BigAutoField(primary_key=True)

    alumno = models.ForeignKey(
        Alumnos,
        on_delete=models.CASCADE,
        related_name="inscripciones",
    )
    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.CASCADE,
        related_name="inscripciones",
    )
    periodo = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.PROTECT,
        related_name="inscripciones",
    )

    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default="ACTIVA",
    )

    creation = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    update = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "Inscripción"
        verbose_name_plural = "Inscripciones"
        # Evitar duplicados del mismo alumno en el mismo grupo y periodo
        unique_together = ("alumno", "grupo", "periodo")

    def __str__(self):
        return f"Inscripción alumno {self.alumno_id} - grupo {self.grupo_id} - periodo {self.periodo_id}"


class Notificacion(models.Model):
    TIPO_CHOICES = (
        ("info", "Información"),
        ("success", "Éxito"),
        ("warning", "Advertencia"),
        ("error", "Error"),
    )

    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notificaciones",
    )
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default="info",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"Notificación para {self.usuario.username}: {self.mensaje[:20]}..."
