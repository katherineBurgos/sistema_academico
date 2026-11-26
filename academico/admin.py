from django.contrib import admin

from .models import (
    AsignacionTutoria, Carrera, CertificadoAprobacion, Curso, Estudiante,
    Facultad, HorarioSeccion, Matricula, Nota, Periodo, Profesor, Seccion,
    Semestre, SesionTutoria, Universidad,
)


class BaseAdmin(admin.ModelAdmin):
    """Muestra quién y cuándo en solo lectura, y guarda el usuario que registra."""
    readonly_fields = ("user", "fecha_creacion", "fecha_modificacion")

    def save_model(self, request, obj, form, change):
        obj.user = request.user                    # quién lo registró o modificó
        super().save_model(request, obj, form, change)


@admin.register(Universidad)
class UniversidadAdmin(BaseAdmin):
    list_display = ("siglas", "nombre", "ciudad")
    search_fields = ("nombre", "siglas")


@admin.register(Facultad)
class FacultadAdmin(BaseAdmin):
    list_display = ("nombre", "universidad", "decano")
    search_fields = ("nombre",)
    list_filter = ("universidad",)


@admin.register(Carrera)
class CarreraAdmin(BaseAdmin):
    list_display = ("codigo", "nombre", "facultad", "duracion_semestres")
    search_fields = ("codigo", "nombre")
    list_filter = ("facultad",)


@admin.register(Semestre)
class SemestreAdmin(BaseAdmin):
    list_display = ("numero", "nombre")


@admin.register(Periodo)
class PeriodoAdmin(BaseAdmin):
    list_display = ("nombre", "fecha_inicio", "fecha_fin", "activo")
    list_filter = ("activo",)


@admin.register(Curso)
class CursoAdmin(BaseAdmin):
    list_display = ("codigo", "nombre", "carrera", "semestre", "creditos")
    search_fields = ("codigo", "nombre")
    list_filter = ("carrera", "semestre")


@admin.register(Profesor)
class ProfesorAdmin(BaseAdmin):
    list_display = ("apellidos", "nombres", "cedula", "titulo")
    search_fields = ("cedula", "apellidos", "nombres")


@admin.register(Estudiante)
class EstudianteAdmin(BaseAdmin):
    list_display = ("apellidos", "nombres", "cedula", "carrera", "cuenta")
    search_fields = ("cedula", "apellidos", "nombres", "cuenta__username")
    list_filter = ("carrera",)


@admin.register(Seccion)
class SeccionAdmin(BaseAdmin):
    list_display = ("curso", "paralelo", "jornada", "periodo", "profesor", "cupo", "inscritos")
    list_filter = ("periodo", "jornada")
    search_fields = ("curso__codigo", "curso__nombre")


@admin.register(HorarioSeccion)
class HorarioSeccionAdmin(BaseAdmin):
    list_display = ("seccion", "dia", "hora_inicio", "hora_fin", "aula")
    list_filter = ("dia", "seccion__periodo", "seccion__jornada")
    search_fields = ("seccion__curso__codigo", "seccion__curso__nombre", "aula")


class NotaInline(admin.StackedInline):             # la Nota se edita dentro de la Matrícula
    model = Nota
    max_num = 1
    extra = 1
    readonly_fields = ("promedio", "estado")
    fields = ("n1", "n2", "n3", "promedio", "estado")


@admin.register(Matricula)
class MatriculaAdmin(BaseAdmin):
    list_display = ("estudiante", "seccion", "fecha")
    list_filter = ("seccion__periodo", "seccion__jornada")
    search_fields = ("estudiante__cedula", "estudiante__apellidos")
    inlines = [NotaInline]

    def save_formset(self, request, form, formset, change):
        instancias = formset.save(commit=False)
        for obj in instancias:
            obj.user = request.user
            obj.save()                              # save() calcula promedio y estado
        formset.save_m2m()


@admin.register(Nota)
class NotaAdmin(BaseAdmin):
    list_display = ("matricula", "n1", "n2", "n3", "promedio", "estado")
    list_filter = ("estado",)
    readonly_fields = BaseAdmin.readonly_fields + ("promedio", "estado")


@admin.register(AsignacionTutoria)
class AsignacionTutoriaAdmin(BaseAdmin):
    list_display = ("estudiante", "tutor", "fecha_inicio", "fecha_fin", "activa")
    list_filter = ("activa", "tutor")
    search_fields = ("estudiante__cedula", "estudiante__apellidos", "tutor__apellidos")


@admin.register(SesionTutoria)
class SesionTutoriaAdmin(BaseAdmin):
    list_display = ("asignacion", "fecha", "tema", "modalidad", "estado")
    list_filter = ("modalidad", "estado")
    search_fields = ("asignacion__estudiante__apellidos", "tema")


@admin.register(CertificadoAprobacion)
class CertificadoAprobacionAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre_estudiante", "curso", "promedio", "fecha_emision")
    search_fields = ("codigo", "nombre_estudiante", "cedula_estudiante", "curso")
    readonly_fields = (
        "matricula", "codigo", "nombre_estudiante", "cedula_estudiante",
        "curso", "periodo", "promedio", "fecha_emision", "qr", "user",
        "fecha_creacion", "fecha_modificacion",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
