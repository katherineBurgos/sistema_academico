from django.contrib import admin

from .models import (
    Carrera, Curso, Estudiante, Facultad, Matricula, Nota, Periodo,
    Profesor, Seccion, Semestre, Universidad,
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
    list_display = ("apellidos", "nombres", "cedula", "carrera")
    search_fields = ("cedula", "apellidos", "nombres")
    list_filter = ("carrera",)


@admin.register(Seccion)
class SeccionAdmin(BaseAdmin):
    list_display = ("curso", "paralelo", "jornada", "periodo", "profesor", "cupo", "inscritos")
    list_filter = ("periodo", "jornada")
    search_fields = ("curso__codigo", "curso__nombre")


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
