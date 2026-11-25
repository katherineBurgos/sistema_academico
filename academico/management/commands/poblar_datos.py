"""Crea datos de prueba: python manage.py poblar_datos
Se puede ejecutar varias veces: usa get_or_create y no duplica."""
import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from academico.models import (
    Carrera, Curso, EstadoNota, Estudiante, Facultad, Jornada, Matricula, Nota,
    Periodo, Profesor, Seccion, Semestre, Universidad,
)

NOMBRES = ["Ana", "Luis", "Eva", "Carlos", "María", "José", "Sofía"]
APELLIDOS = ["Pérez", "Mora", "Ruiz", "Vera", "León", "Torres", "Ríos"]
TOTAL_DEMO = 7
CEDULAS_DEMO_SOBRANTES = tuple(f"09{i:08d}" for i in range(TOTAL_DEMO + 1, 12))
SECCIONES_DEMO_SOBRANTES = (
    ("RED-101", "B", Jornada.NOCTURNA),
    ("RED-102", "A", Jornada.DIURNA),
    ("RED-102", "B", Jornada.NOCTURNA),
    ("RED-201", "A", Jornada.DIURNA),
)


class Command(BaseCommand):
    help = "Crea datos de prueba para el sistema académico"

    @transaction.atomic
    def handle(self, *args, **options):
        ug, _ = Universidad.objects.get_or_create(
            nombre="Universidad de Guayaquil", defaults={"siglas": "UG", "ciudad": "Guayaquil"})
        espol, _ = Universidad.objects.get_or_create(
            nombre="Escuela Politécnica del Litoral", defaults={"siglas": "ESPOL", "ciudad": "Guayaquil"})

        f_mat, _ = Facultad.objects.get_or_create(universidad=ug, nombre="Ciencias Matemáticas y Físicas")
        f_ind, _ = Facultad.objects.get_or_create(universidad=ug, nombre="Ingeniería Industrial")
        Facultad.objects.get_or_create(universidad=espol, nombre="Ing. Electricidad y Computación")

        sof, _ = Carrera.objects.get_or_create(codigo="SOF", defaults={"facultad": f_mat, "nombre": "Software"})
        red, _ = Carrera.objects.get_or_create(
            codigo="RED", defaults={"facultad": f_mat, "nombre": "Redes y Telecomunicaciones"})
        Carrera.objects.get_or_create(
            codigo="IND", defaults={"facultad": f_ind, "nombre": "Ingeniería Industrial", "duracion_semestres": 10})

        s1, _ = Semestre.objects.get_or_create(numero=1, defaults={"nombre": "Primer semestre"})
        s2, _ = Semestre.objects.get_or_create(numero=2, defaults={"nombre": "Segundo semestre"})

        periodo, _ = Periodo.objects.get_or_create(
            nombre="2026-1", defaults={"fecha_inicio": datetime.date(2026, 4, 1),
                                       "fecha_fin": datetime.date(2026, 8, 31), "activo": True})

        cursos = {}
        for codigo, nombre, carrera, sem, cred in [
            ("SOF-101", "Programación I", sof, s1, 4),
            ("SOF-102", "Matemática discreta", sof, s1, 3),
            ("SOF-201", "Programación II", sof, s2, 4),
            ("RED-101", "Fundamentos de redes", red, s1, 4),
            ("RED-102", "Electrónica básica", red, s1, 3),
            ("RED-201", "Enrutamiento", red, s2, 4),
        ]:
            cursos[codigo], _ = Curso.objects.get_or_create(
                codigo=codigo, defaults={"carrera": carrera, "semestre": sem, "nombre": nombre, "creditos": cred})

        vera, _ = Profesor.objects.get_or_create(
            cedula="0911111111", defaults={"apellidos": "Vera", "nombres": "Carlos", "titulo": "Mg. en Software"})
        leon, _ = Profesor.objects.get_or_create(
            cedula="0922222222", defaults={"apellidos": "León", "nombres": "María", "titulo": "Ing. en Redes"})
        Profesor.objects.get_or_create(
            cedula="0933333333", defaults={"apellidos": "Salas", "nombres": "Jorge", "titulo": "PhD. en Matemática"})

        secciones = []
        for codigo, prof, paralelo, jornada, cupo in [
            ("SOF-101", vera, "A", Jornada.DIURNA, 30),
            ("SOF-101", leon, "B", Jornada.NOCTURNA, 25),
            ("SOF-102", vera, "A", Jornada.DIURNA, 30),
            ("SOF-102", leon, "B", Jornada.NOCTURNA, 25),
            ("SOF-201", vera, "A", Jornada.DIURNA, 30),
            ("SOF-201", leon, "B", Jornada.NOCTURNA, 25),
            ("RED-101", leon, "A", Jornada.DIURNA, 30),
        ]:
            sec, _ = Seccion.objects.get_or_create(
                curso=cursos[codigo], periodo=periodo, paralelo=paralelo, jornada=jornada,
                defaults={"profesor": prof, "cupo": cupo})
            secciones.append(sec)

        # Los estudiantes se distribuyen entre Software y Redes.
        estudiantes = []
        for i in range(TOTAL_DEMO):
            est, _ = Estudiante.objects.get_or_create(
                cedula=f"09{i + 1:08d}",
                defaults={"nombres": NOMBRES[i], "apellidos": APELLIDOS[i],
                          "email": f"{NOMBRES[i].lower()}.{APELLIDOS[i].lower()}@correo.com".replace("í", "i").replace("é", "e").replace("ó", "o").replace("á", "a").replace("ú", "u"),
                          "carrera": sof if i % 2 == 0 else red})
            estudiantes.append(est)

        # Retira estudiantes y secciones sobrantes de la carga anterior de 11 registros.
        Matricula.objects.filter(estudiante__cedula__in=CEDULAS_DEMO_SOBRANTES).delete()
        Estudiante.objects.filter(cedula__in=CEDULAS_DEMO_SOBRANTES).delete()

        # Cada estudiante se matricula en una sección de su carrera.
        for i, est in enumerate(estudiantes):
            propias = [s for s in secciones if s.curso.carrera_id == est.carrera_id]
            sec = propias[i % len(propias)]
            matriculas = list(Matricula.objects.filter(estudiante=est).order_by("pk"))
            mat = next((m for m in matriculas if m.seccion_id == sec.pk), None)
            if mat is None and matriculas:
                mat = matriculas[0]
                mat.seccion = sec
                mat.save(update_fields=["seccion"])
            elif mat is None:
                mat = Matricula.objects.create(estudiante=est, seccion=sec)

            Matricula.objects.filter(estudiante=est).exclude(pk=mat.pk).delete()
            nota, _ = Nota.objects.get_or_create(
                matricula=mat,
                defaults={
                    "n1": Decimal("90"),
                    "n2": Decimal("90"),
                    "n3": Decimal("90"),
                },
            )
            if nota.estado != EstadoNota.APROBADO:
                nota.n1 = Decimal("90")
                nota.n2 = Decimal("90")
                nota.n3 = Decimal("90")
                nota.save()

        for codigo, paralelo, jornada in SECCIONES_DEMO_SOBRANTES:
            Seccion.objects.filter(
                curso=cursos[codigo],
                periodo=periodo,
                paralelo=paralelo,
                jornada=jornada,
            ).delete()

        self.stdout.write(self.style.SUCCESS(
            f"Datos listos: {Estudiante.objects.count()} estudiantes, "
            f"{Seccion.objects.count()} secciones, {Matricula.objects.count()} matrículas, "
            f"{Nota.objects.count()} notas."))
