from django.shortcuts import get_object_or_404
from rest_framework import permissions, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction

from eduplan_api.models import Notificacion
from eduplan_api.serializers import NotificacionSerializer

class NotificacionesView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Obtener notificaciones del usuario logueado
    def get(self, request, *args, **kwargs):
        notificaciones = Notificacion.objects.filter(usuario=request.user).order_by("-fecha_creacion")
        data = NotificacionSerializer(notificaciones, many=True).data
        return Response(data, 200)

    # Eliminar una notificación (marcar como leída/borrada)
    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        notificacion_id = request.GET.get("id")
        if not notificacion_id:
            return Response({"details": "ID de notificación requerido"}, status=status.HTTP_400_BAD_REQUEST)

        notificacion = get_object_or_404(Notificacion, id=notificacion_id, usuario=request.user)
        notificacion.delete()
        
        return Response({"details": "Notificación eliminada"}, 200)
