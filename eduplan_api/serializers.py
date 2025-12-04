from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from eduplan_api.models import *


class UserSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ('id','first_name','last_name', 'email')

class AdminSerializer(serializers.ModelSerializer):
    user=UserSerializer(read_only=True)
    class Meta:
        model = Administradores
        fields = '__all__'

class AlumnoSerializer(serializers.ModelSerializer):
    user=UserSerializer(read_only=True)
    class Meta:
        model = Alumnos
        fields = "__all__"

class MaestroSerializer(serializers.ModelSerializer):
    user=UserSerializer(read_only=True)
    class Meta:
        model = Maestros
        fields = '__all__'

# Serializer personalizado para incluir rol y perfil en el token
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Genera access y refresh y valida credenciales
        data = super().validate(attrs)
        user = self.user

        roles = list(user.groups.values_list("name", flat=True))
        rol = roles[0] if roles else None
        data["rol"] = rol

        if rol == "alumno":
            alumno = Alumnos.objects.filter(user=user).first()
            data["perfil"] = AlumnoSerializer(alumno).data if alumno else None

        elif rol == "maestro":
            maestro = Maestros.objects.filter(user=user).first()
            data["perfil"] = MaestroSerializer(maestro).data if maestro else None

        elif rol == "administrador":
            data["perfil"] = UserSerializer(user, many=False).data

        else:
            data["perfil"] = None

        return data


class PeriodoAcademicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodoAcademico
        fields = '__all__'


class MateriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Materia
        fields = '__all__'


class GrupoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grupo
        fields = "__all__"

    def validate_cupo_maximo(self, value):
        if value is None:
            raise serializers.ValidationError("El cupo máximo es obligatorio.")
        if value <= 0:
            raise serializers.ValidationError("El cupo máximo debe ser mayor que cero.")
        return value


class AulaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aula
        fields = '__all__'


class HorarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Horario
        fields = '__all__'


class SolicitudCambioSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolicitudCambio
        fields = "__all__"

    def validate(self, attrs):
        """
        Valida que hora_inicio_propuesta < hora_fin_propuesta.
        Soporta tanto creación como actualización parcial.
        """
        instance = getattr(self, "instance", None)

        hora_inicio = attrs.get(
            "hora_inicio_propuesta",
            getattr(instance, "hora_inicio_propuesta", None),
        )
        hora_fin = attrs.get(
            "hora_fin_propuesta",
            getattr(instance, "hora_fin_propuesta", None),
        )

        if hora_inicio and hora_fin and hora_inicio >= hora_fin:
            raise serializers.ValidationError(
                {
                    "hora_inicio_propuesta": "La hora de inicio debe ser menor que la hora de fin.",
                    "hora_fin_propuesta": "La hora de fin debe ser mayor que la hora de inicio.",
                }
            )

        return attrs

class InscripcionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inscripcion
        fields = "__all__"


class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = "__all__"
