from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from .models import (
    AsignacionTutoria, Carrera, Curso, EstadoNota, Estudiante,
    Facultad, Jornada, Matricula, Nota, Periodo, Profesor,
    Seccion, Universidad,
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
            "horarios",
            "matriculas",
            "notas",
            "asignaciones-tutoria",
            "sesiones-tutoria",
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
        for ruta in (
            "/academico/mi-matricula/",
            "/academico/certificados/",
            "/academico/certificados/aprobacion/1/",
            "/academico/certificados/verificar/00000000-0000-0000-0000-000000000000/",
        ):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 404)

        seccion_form = self.client.get(
            reverse("academico:crear", kwargs={"modelo": "secciones"})
        )
        self.assertContains(seccion_form, "Vespertino")
        self.assertContains(seccion_form, "Nocturno")
        self.assertNotContains(seccion_form, "Diurna")

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

    def test_related_records_prevent_deletion(self):
        universidad = Universidad.objects.create(
            nombre="Universidad protegida",
            siglas="UPR",
            ciudad="Quito",
            user=self.usuario,
        )
        Facultad.objects.create(
            universidad=universidad,
            nombre="Facultad protegida",
            user=self.usuario,
        )
        eliminar_url = reverse(
            "academico:eliminar",
            kwargs={"modelo": "universidades", "pk": universidad.pk},
        )

        response = self.client.post(eliminar_url, follow=True)

        self.assertRedirects(
            response,
            reverse("academico:lista", kwargs={"modelo": "universidades"}),
        )
        self.assertTrue(Universidad.objects.filter(pk=universidad.pk).exists())
        self.assertContains(response, "No se puede eliminar")


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

    def test_schedule_list_shows_both_jornadas(self):
        call_command("poblar_datos")
        usuario = get_user_model().objects.create_user(username="horarios")
        client = self.client_class()
        client.force_login(usuario)

        response = client.get(
            reverse("academico:lista", kwargs={"modelo": "horarios"})
        )

        self.assertContains(response, "Jornada")
        self.assertContains(response, "Vespertino")
        self.assertContains(response, "Nocturno")

    def test_seed_removes_records_left_by_eleven_record_version(self):
        call_command("poblar_datos")
        periodo = Periodo.objects.get(nombre="2026-1")
        curso_red = Curso.objects.get(codigo="RED-101")
        seccion_red = Seccion.objects.get(
            curso=curso_red,
            periodo=periodo,
            paralelo="A",
            jornada=Jornada.VESPERTINA,
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
            ("RED-102", "A", Jornada.VESPERTINA),
            ("RED-102", "B", Jornada.NOCTURNA),
            ("RED-201", "A", Jornada.VESPERTINA),
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


class ExportacionesTests(TestCase):
    def setUp(self):
        usuario = get_user_model().objects.create_user(
            username="exportador",
            password="Dahlia-River-4092!",
        )
        self.client.force_login(usuario)
        universidad = Universidad.objects.create(
            nombre="Universidad de exportación",
            siglas="UE",
            ciudad="Quito",
            user=usuario,
        )
        facultad = Facultad.objects.create(
            universidad=universidad,
            nombre="Facultad de exportación",
            user=usuario,
        )
        self.carrera = Carrera.objects.create(
            facultad=facultad,
            codigo="EXP",
            nombre="Carrera de exportación",
            user=usuario,
        )

    def test_excel_exports_all_filtered_rows_and_only_allowed_columns(self):
        for numero in range(12):
            Estudiante.objects.create(
                cedula=f"08{numero:08d}",
                nombres=f"Grupo {numero}",
                apellidos="Prueba",
                carrera=self.carrera,
            )
        url = reverse("academico:lista", kwargs={"modelo": "estudiantes"})

        response = self.client.get(
            url,
            {
                "texto": "Grupo",
                "campos": ["nombres", "campo_no_permitido"],
                "exportar": "excel",
            },
        )

        self.assertEqual(response.status_code, 200)
        libro = load_workbook(BytesIO(response.content), read_only=True)
        hoja = libro.active
        self.assertEqual(hoja.max_column, 1)
        self.assertEqual(hoja["A3"].value, "Nombres")
        self.assertEqual(hoja.max_row, 15)
        self.assertEqual(hoja["A15"].value, "Grupo 9")

    def test_pdf_export_returns_a_pdf_document(self):
        Estudiante.objects.create(
            cedula="0712345678",
            nombres="Grupo",
            apellidos="Prueba",
            carrera=self.carrera,
        )
        url = reverse("academico:lista", kwargs={"modelo": "estudiantes"})

        response = self.client.get(url, {"exportar": "pdf"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))


class MatriculaNotasTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="matriculas",
            password="Dahlia-River-4092!",
        )
        self.client.force_login(self.usuario)
        call_command("poblar_datos")
        estudiante = Estudiante.objects.first()
        estudiante.cuenta = self.usuario
        estudiante.save(update_fields=["cuenta"])

    def test_editing_enrollment_saves_its_note_in_the_same_form(self):
        nota = Nota.objects.filter(
            matricula__estudiante__cuenta=self.usuario,
        ).select_related("matricula").first()
        matricula = nota.matricula
        url = reverse(
            "academico:editar",
            kwargs={"modelo": "matriculas", "pk": matricula.pk},
        )
        datos = {
            "estudiante": matricula.estudiante_id,
            "seccion": matricula.seccion_id,
            "fecha": matricula.fecha.isoformat(),
            "nota-TOTAL_FORMS": "1",
            "nota-INITIAL_FORMS": "1",
            "nota-MIN_NUM_FORMS": "0",
            "nota-MAX_NUM_FORMS": "1",
            "nota-0-id": nota.pk,
            "nota-0-n1": "88",
            "nota-0-n2": "89",
            "nota-0-n3": "90",
        }

        response = self.client.post(url, datos)

        self.assertRedirects(
            response,
            reverse("academico:lista", kwargs={"modelo": "matriculas"}),
        )
        nota.refresh_from_db()
        self.assertEqual(nota.n1, Decimal("88.00"))
        self.assertEqual(nota.promedio, Decimal("89.00"))


class TutoriasYCertificadosTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="tutorias",
            password="Dahlia-River-4092!",
        )
        self.client.force_login(self.usuario)
        call_command("poblar_datos")
        estudiante = Estudiante.objects.first()
        estudiante.cuenta = self.usuario
        estudiante.save(update_fields=["cuenta"])

    def test_student_cannot_have_two_active_tutors(self):
        estudiante = Estudiante.objects.first()
        profesores = list(Profesor.objects.all()[:2])
        AsignacionTutoria.objects.create(
            estudiante=estudiante,
            tutor=profesores[0],
        )
        segunda = AsignacionTutoria(
            estudiante=estudiante,
            tutor=profesores[1],
        )

        with self.assertRaises(ValidationError):
            segunda.full_clean()
