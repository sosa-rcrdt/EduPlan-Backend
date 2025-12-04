import os
import django
import random
from datetime import date, time, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eduplan_api.settings')
django.setup()

from django.contrib.auth.models import User
from eduplan_api.models import (
    Administradores, Alumnos, Maestros, PeriodoAcademico,
    Materia, Grupo, Aula, Horario, Inscripcion
)

def create_users():
    print("Creating Users...")
    
    # Admin
    if not User.objects.filter(username='admin_test').exists():
        user = User.objects.create_user('admin_test', 'admin@test.com', 'password123')
        user.first_name = "Admin"
        user.last_name = "Test"
        user.save()
        Administradores.objects.create(
            user=user,
            clave_admin="ADM001",
            telefono="5551234567",
            rfc="ADMINRFC001",
            edad=30,
            ocupacion="Administrador"
        )
        print("Admin created.")

    # Maestros
    maestros = []
    for i in range(1, 4):
        username = f'maestro{i}'
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(username, f'maestro{i}@test.com', 'password123')
            user.first_name = f"Maestro"
            user.last_name = f"{i}"
            user.save()
            maestro = Maestros.objects.create(
                user=user,
                id_trabajador=f"TRAB{i:03d}",
                telefono=f"555000000{i}",
                rfc=f"MAESTRORFC{i:03d}",
                cubiculo=f"C-{i}",
                edad=35 + i,
                area_investigacion="Ciencias"
            )
            maestros.append(maestro)
            print(f"Maestro {i} created.")
        else:
            maestros.append(Maestros.objects.get(user__username=username))
    
    # Alumnos
    alumnos = []
    for i in range(1, 6):
        username = f'alumno{i}'
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(username, f'alumno{i}@test.com', 'password123')
            user.first_name = f"Alumno"
            user.last_name = f"{i}"
            user.save()
            alumno = Alumnos.objects.create(
                user=user,
                matricula=f"2023{i:04d}",
                curp=f"ALUMNOCURP{i:03d}",
                rfc=f"ALUMNORFC{i:03d}",
                edad=20 + i,
                telefono=f"555999999{i}",
                ocupacion="Estudiante"
            )
            alumnos.append(alumno)
            print(f"Alumno {i} created.")
        else:
            alumnos.append(Alumnos.objects.get(user__username=username))

    return maestros, alumnos

def create_academic_data():
    print("Creating Academic Data...")

    # Periodo
    periodo, created = PeriodoAcademico.objects.get_or_create(
        nombre="Primavera 2024",
        defaults={
            "fecha_inicio": date(2024, 1, 15),
            "fecha_fin": date(2024, 5, 30),
            "estado": "ACTIVO"
        }
    )
    if created:
        print("Periodo created.")

    # Materias
    materias = []
    materias_data = [
        ("Matemáticas I", "MAT101", 5, "Ciencias Exactas"),
        ("Física I", "FIS101", 5, "Ciencias Exactas"),
        ("Programación I", "PROG101", 6, "Tecnología"),
        ("Historia", "HIST101", 4, "Humanidades"),
    ]
    for nombre, codigo, creditos, area in materias_data:
        materia, created = Materia.objects.get_or_create(
            codigo=codigo,
            defaults={
                "nombre": nombre,
                "creditos": creditos,
                "area_academica": area
            }
        )
        materias.append(materia)
        if created:
            print(f"Materia {nombre} created.")

    # Aulas
    aulas = []
    for i in range(1, 4):
        aula, created = Aula.objects.get_or_create(
            edificio="A",
            numero=f"10{i}",
            defaults={
                "capacidad": 30,
                "recursos": "Proyector, Pizarrón",
                "estado": "DISPONIBLE"
            }
        )
        aulas.append(aula)
        if created:
            print(f"Aula A-10{i} created.")

    return periodo, materias, aulas

def create_groups_and_schedules(periodo, materias, aulas, maestros, alumnos):
    print("Creating Groups and Schedules...")

    for i, materia in enumerate(materias):
        maestro = maestros[i % len(maestros)]
        grupo, created = Grupo.objects.get_or_create(
            nombre=f"G{i+1}",
            materia=materia,
            defaults={
                "semestre": 1,
                "cupo_maximo": 25
            }
        )
        if created:
            print(f"Grupo {grupo} created.")

            # Horario
            aula = aulas[i % len(aulas)]
            Horario.objects.create(
                periodo=periodo,
                grupo=grupo,
                aula=aula,
                dia_semana=0, # Lunes
                hora_inicio=time(8 + i, 0),
                hora_fin=time(10 + i, 0),
                docente=maestro,
                estado="ACTIVO"
            )
            print(f"Horario for {grupo} created.")

            # Inscripciones
            for alumno in alumnos[:3]: # Enroll first 3 students
                Inscripcion.objects.get_or_create(
                    alumno=alumno,
                    grupo=grupo,
                    periodo=periodo,
                    defaults={"estado": "ACTIVA"}
                )
            print(f"Students enrolled in {grupo}.")

if __name__ == "__main__":
    maestros, alumnos = create_users()
    periodo, materias, aulas = create_academic_data()
    create_groups_and_schedules(periodo, materias, aulas, maestros, alumnos)
    print("Database population complete!")
