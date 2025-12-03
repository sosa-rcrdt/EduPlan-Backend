from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)

urlpatterns = [
    #Version
        path('bootstrap/version', bootstrap.VersionView.as_view()),
    #Create Admin
        path('admin/', users.AdminView.as_view()),
    #Admin Data
        path('lista-admins/', users.AdminAll.as_view()),
    #Edit Admin
        path('admins-edit/', users.AdminsViewEdit.as_view()),
    #Create Alumno
        path('alumnos/', alumnos.AlumnosView.as_view()),
    #Alumno Data
        path('lista-alumnos/', alumnos.AlumnosAll.as_view()),
    #Edit Alumno
        path('alumnos-edit/', alumnos.AlumnosViewEdit.as_view()),
    #Create Maestro
        path('maestros/', maestros.MaestrosView.as_view()),
    #Maestro Data
        path('lista-maestros/', maestros.MaestrosAll.as_view()),
    #Edit Maestro
        path('maestros-edit/', maestros.MaestrosViewEdit.as_view()),
    #Login
        path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
        path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
        path('token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    #Logout
        path('logout/', auth.Logout.as_view())

]