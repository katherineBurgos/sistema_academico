from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.forms import CheckboxInput, Select, modelform_factory
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import TemplateView

from .models import (
    Carrera, Curso, EstadoNota, Estudiante, Facultad, Matricula, Nota, Periodo,
    Profesor, Seccion, Semestre, Universidad,
)


RECURSOS = {
    "universidades": {
        "modelo": Universidad,
        "busqueda": ("nombre", "siglas", "ciudad"),
    },
    "facultades": {
        "modelo": Facultad,
        "busqueda": ("nombre", "decano", "universidad__nombre"),
    },
    "carreras": {
        "modelo": Carrera,
        "busqueda": ("codigo", "nombre", "facultad__nombre"),
    },
    "semestres": {
        "modelo": Semestre,
        "busqueda": ("nombre",),
    },
    "periodos": {
        "modelo": Periodo,
        "busqueda": ("nombre",),
    },
    "cursos": {
        "modelo": Curso,
        "busqueda": ("codigo", "nombre", "carrera__nombre"),
    },
    "profesores": {
        "modelo": Profesor,
        "busqueda": ("cedula", "nombres", "apellidos", "email"),
    },
    "estudiantes": {
        "modelo": Estudiante,
        "busqueda": ("cedula", "nombres", "apellidos", "email", "carrera__nombre"),
    },
    "secciones": {
        "modelo": Seccion,
        "busqueda": (
            "curso__codigo", "curso__nombre", "periodo__nombre",
            "profesor__nombres", "profesor__apellidos",
        ),
    },
    "matriculas": {
        "modelo": Matricula,
        "busqueda": (
            "estudiante__cedula", "estudiante__nombres", "estudiante__apellidos",
            "seccion__curso__codigo", "seccion__curso__nombre",
        ),
    },
    "notas": {
        "modelo": Nota,
        "busqueda": (
            "matricula__estudiante__cedula", "matricula__estudiante__nombres",
            "matricula__estudiante__apellidos", "matricula__seccion__curso__nombre",
        ),
    },
}

CAMPOS_AUDITORIA = {"user", "fecha_creacion", "fecha_modificacion"}


def _recurso(slug):
    try:
        return RECURSOS[slug]
    except KeyError as exc:
        raise Http404("Apartado no encontrado.") from exc


def _campos_visibles(modelo):
    return [
        campo for campo in modelo._meta.concrete_fields
        if not campo.primary_key and campo.name not in CAMPOS_AUDITORIA
    ]


def _valor_campo(objeto, campo):
    if campo.choices:
        return getattr(objeto, f"get_{campo.name}_display")()
    valor = getattr(objeto, campo.name)
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    return valor


def _configurar_widgets(formulario):
    for campo in formulario.fields.values():
        if isinstance(campo.widget, CheckboxInput):
            clase = "form-check-input"
        elif isinstance(campo.widget, Select):
            clase = "form-select"
        else:
            clase = "form-control"
        campo.widget.attrs["class"] = clase
    return formulario


def _url_lista(slug):
    return redirect("academico:lista", modelo=slug)


class InicioView(LoginRequiredMixin, TemplateView):
    """Página de inicio con tarjetas de resumen."""
    template_name = "academico/inicio.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["total_estudiantes"] = Estudiante.objects.count()
        contexto["periodo_activo"] = Periodo.objects.filter(activo=True).first()
        contexto["total_secciones"] = Seccion.objects.filter(periodo__activo=True).count()
        contexto["total_matriculas"] = Matricula.objects.count()
        total = Nota.objects.count()
        aprobados = Nota.objects.filter(estado=EstadoNota.APROBADO).count()
        contexto["total_aprobados"] = aprobados
        contexto["porcentaje_aprobados"] = round(aprobados * 100 / total, 1) if total else 0   # evita dividir entre 0
        return contexto


@login_required
def lista_modelo(request, modelo):
    recurso = _recurso(modelo)
    clase = recurso["modelo"]
    campos = _campos_visibles(clase)
    relaciones = [
        campo.name for campo in clase._meta.fields
        if campo.is_relation and campo.many_to_one
    ]
    consulta = clase.objects.all()
    if relaciones:
        consulta = consulta.select_related(*relaciones)

    termino = request.GET.get("q", "").strip()
    if termino:
        filtros = Q()
        for campo in recurso["busqueda"]:
            filtros |= Q(**{f"{campo}__icontains": termino})
        consulta = consulta.filter(filtros)

    filas = [
        {
            "objeto": objeto,
            "valores": [_valor_campo(objeto, campo) for campo in campos],
        }
        for objeto in consulta
    ]
    return render(request, "academico/lista.html", {
        "modelo": modelo,
        "titulo": clase._meta.verbose_name_plural.capitalize(),
        "singular": clase._meta.verbose_name.capitalize(),
        "campos": campos,
        "filas": filas,
        "termino": termino,
    })


@login_required
def formulario_modelo(request, modelo, pk=None):
    clase = _recurso(modelo)["modelo"]
    objeto = get_object_or_404(clase, pk=pk) if pk is not None else None
    formulario_modelo = modelform_factory(
        clase,
        exclude=CAMPOS_AUDITORIA,
    )
    formulario = formulario_modelo(
        request.POST or None,
        request.FILES or None,
        instance=objeto,
    )
    _configurar_widgets(formulario)

    if request.method == "POST" and formulario.is_valid():
        guardado = formulario.save(commit=False)
        guardado.user = request.user
        guardado.save()
        formulario.save_m2m()
        messages.success(
            request,
            f"{clase._meta.verbose_name.capitalize()} "
            f"{'actualizado' if objeto else 'creado'} correctamente.",
        )
        return _url_lista(modelo)

    return render(request, "academico/formulario.html", {
        "modelo": modelo,
        "titulo": clase._meta.verbose_name.capitalize(),
        "objeto": objeto,
        "formulario": formulario,
    })


@login_required
def eliminar_modelo(request, modelo, pk):
    clase = _recurso(modelo)["modelo"]
    objeto = get_object_or_404(clase, pk=pk)
    if request.method == "POST":
        try:
            objeto.delete()
        except ProtectedError:
            messages.error(
                request,
                "No se puede eliminar porque existen registros relacionados.",
            )
        else:
            messages.success(request, f"{clase._meta.verbose_name.capitalize()} eliminado correctamente.")
        return _url_lista(modelo)

    return render(request, "academico/confirmar_eliminacion.html", {
        "modelo": modelo,
        "titulo": clase._meta.verbose_name.capitalize(),
        "objeto": objeto,
    })
