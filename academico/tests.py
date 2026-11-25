from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import (
    Carrera, Curso, EstadoNota, Estudiante, Facultad, Jornada, Matricula, Nota,
    Periodo, Profesor, Seccion, Universidad,
)


class ModulosAcademicosTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="gestor",
            password="Dahlia-River-4092!",
        )
        self.client.force_login(self.usuario)

    def test_all_modules_have_list_and_create_pages(self):
        modelos = (
            "universidades",
            "facultades",
            "carreras",
            "semestres",
            "periodos",
            "cursos",
            "profesores",
            "estudiantes",
            "secciones",
            "matriculas",
            "notas",
        )
        for modelo in modelos:
            with self.subTest(modelo=modelo):
                lista = self.client.get(
                    reverse("academico:lista", kwargs={"modelo": modelo})
                )
                formulario = self.client.get(
                    reverse("academico:crear", kwargs={"modelo": modelo})
                )
                self.assertEqual(lista.status_code, 200)
                self.assertEqual(formulario.status_code, 200)

    def test_student_can_be_created_searched_updated_and_deleted(self):
        universidad = Universidad.objects.create(
            nombre="Universidad de prueba",
            siglas="UP",
            ciudad="Quito",
            user=self.usuario,
        )
        facultad = Facultad.objects.create(
            universidad=universidad,
            nombre="Facultad de prueba",
            user=self.usuario,
        )
        carrera = Carrera.objects.create(
            facultad=facultad,
            codigo="PRU",
            nombre="Carrera de prueba",
            user=self.usuario,
        )
        datos = {
            "cedula": "0912345678",
            "nombres": "Ana",
            "apellidos": "Prueba",
            "email": "ana@example.com",
            "telefono": "",
            "fecha_nacimiento": "",
            "carrera": carrera.pk,
        }
        crear_url = reverse("academico:crear", kwargs={"modelo": "estudiantes"})
        response = self.client.post(crear_url, datos)
        self.assertRedirects(
            response,
            reverse("academico:lista", kwargs={"modelo": "estudiantes"}),
        )

        estudiante = Estudiante.objects.get(cedula=datos["cedula"])
        self.assertEqual(estudiante.user, self.usuario)
        lista_url = reverse("academico:lista", kwargs={"modelo": "estudiantes"})
        response = self.client.get(lista_url, {"q": "Ana"})
        self.assertContains(response, "Ana")

        editar_url = reverse(
            "academico:editar",
            kwargs={"modelo": "estudiantes", "pk": estudiante.pk},
        )
        datos["nombres"] = "Andrea"
        response = self.client.post(editar_url, datos)
        self.assertRedirects(response, lista_url)
        estudiante.refresh_from_db()
        self.assertEqual(estudiante.nombres, "Andrea")

        eliminar_url = reverse(
            "academico:eliminar",
            kwargs={"modelo": "estudiantes", "pk": estudiante.pk},
        )
        response = self.client.post(eliminar_url)
        self.assertRedirects(response, lista_url)
        self.assertFalse(Estudiante.objects.filter(pk=estudiante.pk).exists())


class DatosDemostracionTests(TestCase):
    def test_seed_creates_seven_students_active_sections_enrollments_and_passes(self):
        call_command("poblar_datos")

        self.assertEqual(Estudiante.objects.count(), 7)
        self.assertEqual(
            Seccion.objects.filter(periodo__activo=True).count(),
            7,
        )
        self.assertEqual(Matricula.objects.count(), 7)
        self.assertEqual(
            Nota.objects.filter(estado=EstadoNota.APROBADO).count(),
            7,
        )
        self.assertEqual(Periodo.objects.filter(activo=True).count(), 1)

        call_command("poblar_datos")
        self.assertEqual(Estudiante.objects.count(), 7)
        self.assertEqual(Matricula.objects.count(), 7)

    def test_seed_removes_records_left_by_eleven_record_version(self):
        call_command("poblar_datos")
        periodo = Periodo.objects.get(nombre="2026-1")
        curso_red = Curso.objects.get(codigo="RED-101")
        seccion_red = Seccion.objects.get(
            curso=curso_red,
            periodo=periodo,
            paralelo="A",
            jornada=Jornada.DIURNA,
        )

        for numero in range(8, 12):
            estudiante = Estudiante.objects.create(
                cedula=f"09{numero:08d}",
                nombres=f"Estudiante {numero}",
                apellidos="Antiguo",
                carrera=curso_red.carrera,
            )
            matricula = Matricula.objects.create(
                estudiante=estudiante,
                seccion=seccion_red,
            )
            Nota.objects.create(
                matricula=matricula,
                n1=Decimal("90"),
                n2=Decimal("90"),
                n3=Decimal("90"),
            )

        profesor = Profesor.objects.get(cedula="0933333333")
        secciones_antiguas = (
            ("RED-101", "B", Jornada.NOCTURNA),
            ("RED-102", "A", Jornada.DIURNA),
            ("RED-102", "B", Jornada.NOCTURNA),
            ("RED-201", "A", Jornada.DIURNA),
        )
        for codigo, paralelo, jornada in secciones_antiguas:
            Seccion.objects.create(
                curso=Curso.objects.get(codigo=codigo),
                periodo=periodo,
                profesor=profesor,
                paralelo=paralelo,
                jornada=jornada,
            )

        call_command("poblar_datos")

        self.assertEqual(Estudiante.objects.count(), 7)
        self.assertEqual(Seccion.objects.filter(periodo__activo=True).count(), 7)
        self.assertEqual(Matricula.objects.count(), 7)
        self.assertEqual(Nota.objects.filter(estado=EstadoNota.APROBADO).count(), 7)
