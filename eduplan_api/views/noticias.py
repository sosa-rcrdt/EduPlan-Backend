from django.shortcuts import render
from rest_framework import generics, status, permissions
from rest_framework.response import Response

from eduplan_api.models import Noticia
from eduplan_api.serializers import NoticiaSerializer

class NoticiasAll(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = []
    pagination_class = None
    queryset = Noticia.objects.all().order_by('-fecha_creacion')
    serializer_class = NoticiaSerializer

class NoticiaView(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = Noticia.objects.all()
    serializer_class = NoticiaSerializer

    def post(self, request, *args, **kwargs):
        if not request.user.groups.filter(name='administrador').exists():
            return Response({'error': 'No tienes permisos para crear noticias'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = NoticiaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NoticiasViewEdit(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def check_permissions(self, request):
        if request.method == 'GET':
            return
        super().check_permissions(request)
    queryset = Noticia.objects.all()
    serializer_class = NoticiaSerializer

    def get_object(self):
        noticia_id = self.request.GET.get('id')
        if not noticia_id:
            noticia_id = self.kwargs.get('pk')
        try:
            return Noticia.objects.get(id=noticia_id)
        except Noticia.DoesNotExist:
            return None

    def put(self, request, *args, **kwargs):
        if not request.user.groups.filter(name='administrador').exists():
            return Response({'error': 'No tienes permisos'}, status=status.HTTP_403_FORBIDDEN)
            
        noticia = self.get_object()
        if not noticia:
            return Response({'error': 'Noticia no encontrada'}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = NoticiaSerializer(noticia, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        if not request.user.groups.filter(name='administrador').exists():
            return Response({'error': 'No tienes permisos'}, status=status.HTTP_403_FORBIDDEN)
            
        noticia = self.get_object()
        if not noticia:
            return Response({'error': 'Noticia no encontrada'}, status=status.HTTP_404_NOT_FOUND)
            
        noticia.delete()
        return Response({'message': 'Noticia eliminada'}, status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        # Desactivamos el permiso solo para GET
        noticia = self.get_object()
        if not noticia:
            return Response({'error': 'Noticia no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        serializer = NoticiaSerializer(noticia)
        return Response(serializer.data)
