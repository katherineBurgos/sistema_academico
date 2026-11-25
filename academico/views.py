from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.forms import modelform_factory
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from core.mixins import ComprobantePdfMixin, ExportarMixin, UsuarioRegistroMixin
from core.utils import valor_campo

from .forms import (
    CarreraForm, EstudianteForm, FiltroRecursoForm, MatriculaForm, NotaFormSet,
    ProfesorForm,
)
from .models import (
    Carrera, Curso, EstadoNota, Estudiante, Facultad, Jornada, Matricula, Nota,
    Periodo, Profesor, Seccion, Semestre, Universidad,
)


RECURSOS = {
    "universidades": {
        "modelo": Universidad,
        "titulo": "Universidades",
        "form_fields": ("nombre", "siglas", "ciudad", "logo"),
        "filtros": ("texto", "ciudad"),
        "texto": ("nombre", "siglas"),
        "lookups": {"ciudad": "ciudad__icontains"},
        "columnas": (
            ("siglas", "Siglas"), ("nombre", "Nombre"), ("ciudad", "Ciudad"),
            ("total_facultades", "N.º de facultades"),
        ),
        "por_defecto": ("siglas", "nombre", "ciudad"),
        "select_related": (),
        "prefetch_related": ("facultades",),
        "reporte": "Listado de universidades",
    },
    "facultades": {
        "modelo": Facultad,
        "titulo": "Facultades",
        "form_fields": ("universidad", "nombre", "decano"),
        "filtros": ("universidad", "texto"),
        "texto": ("nombre", "decano", "universidad__nombre"),
        "lookups": {"universidad": "universidad_id"},
        "columnas": (
            ("universidad__siglas", "Universidad"), ("nombre", "Facultad"),
            ("decano", "Decano"),
        ),
        "por_defecto": ("universidad__siglas", "nombre", "decano"),
        "select_related": ("universidad",),
        "prefetch_related": ("carreras",),
        "reporte": "Listado de facultades",
    },
    "carreras": {
        "modelo": Carrera,
        "titulo": "Carreras",
        "form_fields": ("facultad", "codigo", "nombre", "duracion_semestres"),
        "filtros": ("universidad", "facultad", "texto"),
        "texto": ("codigo", "nombre"),
        "lookups": {
            "universidad": "facultad__universidad_id",
            "facultad": "facultad_id",
        },
        "columnas": (
            ("codigo", "Código"), ("nombre", "Carrera"),
            ("facultad__nombre", "Facultad"), ("duracion_semestres", "Duración"),
        ),
        "por_defecto": ("codigo", "nombre", "facultad__nombre", "duracion_semestres"),
        "select_related": ("facultad__universidad",),
        "prefetch_related": ("cursos__semestre",),
        "reporte": "Listado de carreras",
    },
    "semestres": {
        "modelo": Semestre,
        "titulo": "Semestres",
        "form_fields": ("numero", "nombre"),
        "filtros": (),
        "texto": ("nombre",),
        "columnas": (("numero", "Número"), ("nombre", "Semestre")),
        "por_defecto": ("numero", "nombre"),
        "select_related": (),
        "prefetch_related": ("cursos",),
        "reporte": "Listado de semestres",
    },
    "periodos": {
        "modelo": Periodo,
        "titulo": "Periodos",
        "form_fields": ("nombre", "fecha_inicio", "fecha_fin", "activo"),
        "filtros": ("activo", "anio"),
        "texto": ("nombre",),
        "lookups": {"activo": "activo"},
        "columnas": (
            ("nombre", "Periodo"), ("fecha_inicio", "Inicio"),
            ("fecha_fin", "Fin"), ("activo", "Activo"),
        ),
        "por_defecto": ("nombre", "fecha_inicio", "fecha_fin", "activo"),
        "select_related": (),
        "prefetch_related": ("secciones__matriculas",),
        "reporte": "Listado de periodos",
    },
    "cursos": {
        "modelo": Curso,
        "titulo": "Cursos",
        "form_fields": ("carrera", "semestre", "codigo", "nombre", "creditos"),
        "filtros": ("carrera", "semestre", "texto"),
        "texto": ("codigo", "nombre"),
        "lookups": {"carrera": "carrera_id", "semestre": "semestre_id"},
        "columnas": (
            ("codigo", "Código"), ("nombre", "Curso"),
            ("carrera__nombre", "Carrera"), ("semestre", "Semestre"),
            ("creditos", "Créditos"),
        ),
        "por_defecto": ("codigo", "nombre", "carrera__nombre", "semestre", "creditos"),
        "select_related": ("carrera__facultad", "semestre"),
        "prefetch_related": ("secciones",),
        "reporte": "Listado de cursos",
    },
    "profesores": {
        "modelo": Profesor,
        "titulo": "Profesores",
        "form_fields": ("cedula", "nombres", "apellidos", "email", "titulo"),
        "filtros": ("texto", "periodo"),
        "texto": ("cedula", "nombres", "apellidos", "email"),
        "columnas": (
            ("cedula", "Cédula"), ("apellidos", "Apellidos"),
            ("nombres", "Nombres"), ("titulo", "Título"), ("email", "Correo"),
        ),
        "por_defecto": ("cedula", "apellidos", "nombres", "titulo", "email"),
        "select_related": (),
        "prefetch_related": ("secciones__curso", "secciones__periodo"),
        "reporte": "Listado de profesores",
    },
    "estudiantes": {
        "modelo": Estudiante,
        "titulo": "Estudiantes",
        "form_fields": (
            "cedula", "nombres", "apellidos", "email", "telefono",
            "fecha_nacimiento", "carrera", "foto",
        ),
        "filtros": ("texto", "carrera", "facultad", "nacido_desde", "nacido_hasta"),
        "texto": ("cedula", "nombres", "apellidos"),
        "lookups": {
            "carrera": "carrera_id",
            "facultad": "carrera__facultad_id",
        },
        "date_ranges": {
            "nacido_desde": ("fecha_nacimiento__gte",),
            "nacido_hasta": ("fecha_nacimiento__lte",),
        },
        "columnas": (
            ("cedula", "Cédula"), ("apellidos", "Apellidos"),
            ("nombres", "Nombres"), ("email", "Correo"),
            ("telefono", "Teléfono"), ("fecha_nacimiento", "Nacimiento"),
            ("carrera", "Carrera"), ("carrera__facultad__nombre", "Facultad"),
        ),
        "por_defecto": ("cedula", "apellidos", "nombres", "email", "carrera"),
        "select_related": ("carrera__facultad__universidad",),
        "prefetch_related": ("matriculas__seccion__curso", "matriculas__nota"),
        "reporte": "Listado de estudiantes",
    },
    "secciones": {
        "modelo": Seccion,
        "titulo": "Secciones",
        "form_fields": ("curso", "periodo", "profesor", "paralelo", "jornada", "cupo"),
        "filtros": ("periodo", "carrera", "jornada", "profesor"),
        "lookups": {
            "periodo": "periodo_id",
            "carrera": "curso__carrera_id",
            "jornada": "jornada",
            "profesor": "profesor_id",
        },
        "columnas": (
            ("curso", "Curso"), ("paralelo", "Paralelo"),
            ("jornada", "Jornada"), ("profesor", "Profesor"),
            ("cupo", "Cupo"), ("inscritos", "Inscritos"),
        ),
        "por_defecto": ("curso", "paralelo", "jornada", "profesor", "cupo", "inscritos"),
        "select_related": ("curso__carrera", "curso__semestre", "periodo", "profesor"),
        "prefetch_related": ("matriculas__estudiante", "matriculas__nota"),
        "reporte": "Acta de calificaciones",
    },
    "matriculas": {
        "modelo": Matricula,
        "titulo": "Matrículas",
        "form_fields": ("estudiante", "seccion", "fecha"),
        "filtros": (
            "texto", "periodo", "carrera", "curso", "jornada", "estado",
            "promedio_desde", "promedio_hasta",
        ),
        "texto": ("estudiante__cedula", "estudiante__nombres", "estudiante__apellidos"),
        "lookups": {
            "periodo": "seccion__periodo_id",
            "carrera": "seccion__curso__carrera_id",
            "curso": "seccion__curso_id",
            "jornada": "seccion__jornada",
            "estado": "nota__estado",
        },
        "ranges": {
            "promedio_desde": "nota__promedio__gte",
            "promedio_hasta": "nota__promedio__lte",
        },
        "columnas": (
            ("estudiante__cedula", "Cédula"), ("estudiante", "Estudiante"),
            ("seccion__curso__nombre", "Curso"), ("seccion__paralelo", "Paralelo"),
            ("seccion__jornada", "Jornada"), ("seccion__periodo__nombre", "Periodo"),
            ("seccion__profesor", "Profesor"), ("nota__n1", "Nota 1"),
            ("nota__n2", "Nota 2"), ("nota__n3", "Nota 3"),
            ("nota__promedio", "Promedio"), ("nota__estado", "Estado"),
            ("fecha", "Fecha"),
        ),
        "por_defecto": (
            "estudiante__cedula", "estudiante", "seccion__curso__nombre",
            "seccion__jornada", "nota__promedio", "nota__estado",
        ),
        "select_related": (
            "estudiante__carrera", "seccion__curso__carrera", "seccion__curso__semestre",
            "seccion__periodo", "seccion__profesor", "nota",
        ),
        "prefetch_related": (),
        "reporte": "Reporte de matrículas y notas",
    },
    "notas": {
        "modelo": Nota,
        "titulo": "Notas",
        "form_fields": ("matricula", "n1", "n2", "n3"),
        "filtros": ("texto", "periodo", "jornada", "estado", "promedio_desde", "promedio_hasta"),
        "texto": ("matricula__estudiante__cedula", "matricula__estudiante__apellidos"),
        "lookups": {
            "periodo": "matricula__seccion__periodo_id",
            "jornada": "matricula__seccion__jornada",
            "estado": "estado",
        },
        "ranges": {
            "promedio_desde": "promedio__gte",
            "promedio_hasta": "promedio__lte",
        },
        "columnas": (
            ("matricula__estudiante", "Estudiante"),
            ("matricula__seccion__curso", "Curso"),
            ("matricula__seccion__periodo", "Periodo"),
            ("n1", "Nota 1"), ("n2", "Nota 2"), ("n3", "Nota 3"),
            ("promedio", "Promedio"), ("estado", "Estado"),
        ),
        "por_defecto": ("matricula__estudiante", "matricula__seccion__curso", "promedio", "estado"),
        "select_related": ("matricula__estudiante", "matricula__seccion__curso", "matricula__seccion__periodo"),
        "prefetch_related": (),
        "reporte": "Listado de notas",
    },
}

FORMULARIOS = {
    Estudiante: EstudianteForm,
    Profesor: ProfesorForm,
    Carrera: CarreraForm,
    Matricula: MatriculaForm,
}


def _recurso(slug):
    try:
        return RECURSOS[slug]
    except KeyError as exc:
        raise Http404("Apartado no encontrado.") from exc


def _anexar_relacion(queryset, recurso):
    if recurso.get("select_related"):
        queryset = queryset.select_related(*recurso["select_related"])
    if recurso.get("prefetch_related"):
        queryset = queryset.prefetch_related(*recurso["prefetch_related"])
    return queryset


def _tabla(titulo, encabezados, objetos, rutas):
    return {
        "titulo": titulo,
        "encabezados": encabezados,
        "filas": [
            [valor_campo(objeto, ruta) for ruta in rutas]
            for objeto in objetos
        ],
    }


def _tablas_relacionadas(modelo, objeto):
    if modelo is Estudiante:
        return [_tabla(
            "Matrículas y notas",
            ("Fecha", "Curso", "Paralelo", "Jornada", "Periodo", "Promedio", "Estado"),
            objeto.matriculas.select_related(
                "seccion__curso", "seccion__periodo", "nota",
            ).order_by("-fecha"),
            ("fecha", "seccion__curso", "seccion__paralelo", "seccion__jornada",
             "seccion__periodo", "nota__promedio", "nota__estado"),
        )]
    if modelo is Universidad:
        filas = []
        facultades = Facultad.objects.filter(universidad=objeto).prefetch_related("carreras")
        for facultad in facultades:
            carreras = list(facultad.carreras.all())
            if carreras:
                filas.extend(
                    (facultad.nombre, facultad.decano, carrera.nombre)
                    for carrera in carreras
                )
            else:
                filas.append((facultad.nombre, facultad.decano, ""))
        return [{
            "titulo": "Facultades y carreras",
            "encabezados": ("Facultad", "Decano", "Carrera"),
            "filas": filas,
        }]
    if modelo is Facultad:
        return [_tabla(
            "Carreras",
            ("Código", "Carrera", "Duración"),
            objeto.carreras.all(),
            ("codigo", "nombre", "duracion_semestres"),
        )]
    if modelo is Carrera:
        return [_tabla(
            "Malla curricular",
            ("Semestre", "Código", "Curso", "Créditos"),
            objeto.cursos.select_related("semestre").order_by("semestre__numero", "codigo"),
            ("semestre", "codigo", "nombre", "creditos"),
        )]
    if modelo is Semestre:
        return [_tabla(
            "Cursos",
            ("Código", "Curso", "Carrera", "Créditos"),
            objeto.cursos.select_related("carrera"),
            ("codigo", "nombre", "carrera", "creditos"),
        )]
    if modelo is Periodo:
        return [_tabla(
            "Secciones e inscritos",
            ("Curso", "Paralelo", "Jornada", "Profesor", "Inscritos", "Cupo"),
            objeto.secciones.select_related("curso", "profesor").prefetch_related("matriculas"),
            ("curso", "paralelo", "jornada", "profesor", "inscritos", "cupo"),
        )]
    if modelo is Curso:
        return [_tabla(
            "Secciones",
            ("Periodo", "Paralelo", "Jornada", "Profesor", "Inscritos", "Cupo"),
            objeto.secciones.select_related("periodo", "profesor").prefetch_related("matriculas"),
            ("periodo", "paralelo", "jornada", "profesor", "inscritos", "cupo"),
        )]
    if modelo is Profesor:
        periodo_activo = Periodo.objects.filter(activo=True).first()
        secciones = objeto.secciones.select_related("curso", "periodo").prefetch_related("matriculas")
        if periodo_activo:
            secciones = secciones.filter(periodo=periodo_activo)
        return [_tabla(
            "Carga académica del periodo activo",
            ("Curso", "Paralelo", "Jornada", "Periodo", "Inscritos"),
            secciones,
            ("curso", "paralelo", "jornada", "periodo", "inscritos"),
        )]
    if modelo is Seccion:
        return [_tabla(
            "Acta de calificaciones",
            ("Cédula", "Estudiante", "Nota 1", "Nota 2", "Nota 3", "Promedio", "Estado"),
            objeto.matriculas.select_related("estudiante", "nota"),
            ("estudiante__cedula", "estudiante", "nota__n1", "nota__n2",
             "nota__n3", "nota__promedio", "nota__estado"),
        )]
    if modelo is Matricula:
        try:
            nota = objeto.nota
        except Nota.DoesNotExist:
            nota = None
        return [_tabla(
            "Notas",
            ("Nota 1", "Nota 2", "Nota 3", "Promedio", "Estado"),
            [nota] if nota else [],
            ("n1", "n2", "n3", "promedio", "estado"),
        )]
    return []


class RecursoMixin:
    def dispatch(self, request, *args, **kwargs):
        self.recurso = _recurso(kwargs["modelo"])
        self.model = self.recurso["modelo"]
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.model._meta.ordering:
            queryset = queryset.order_by("pk")
        return _anexar_relacion(queryset, self.recurso)

    def get_form_class(self):
        return FORMULARIOS.get(self.recurso["modelo"]) or modelform_factory(
            self.recurso["modelo"],
            fields=self.recurso["form_fields"],
        )

    def get_success_url(self):
        return reverse("academico:lista", kwargs={"modelo": self.kwargs["modelo"]})

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update({
            "modelo": self.kwargs["modelo"],
            "titulo": self.recurso["modelo"]._meta.verbose_name.capitalize(),
            "singular": self.recurso["modelo"]._meta.verbose_name.capitalize(),
            "objeto": getattr(self, "object", None),
        })
        if "form" in contexto:
            contexto["formulario"] = contexto["form"]
        return contexto

    def get_form(self, form_class=None):
        formulario = super().get_form(form_class)
        for campo in formulario.fields.values():
            if isinstance(campo.widget, type(forms.CheckboxInput())):
                clase = "form-check-input"
            elif isinstance(campo.widget, type(forms.Select())):
                clase = "form-select"
            else:
                clase = "form-control"
            campo.widget.attrs["class"] = clase
        return formulario


class RecursoListView(LoginRequiredMixin, RecursoMixin, ExportarMixin, ListView):
    template_name = "academico/lista.html"
    context_object_name = "registros"
    paginate_by = 10
    filtro_form_class = FiltroRecursoForm

    def get_filtro_form(self):
        return self.filtro_form_class(
            self.request.GET or None,
            campos=self.recurso["filtros"],
        )

    @property
    def campos_disponibles(self):
        return self.recurso["columnas"]

    @property
    def campos_por_defecto(self):
        return self.recurso["por_defecto"]

    @property
    def titulo_reporte(self):
        return self.recurso["reporte"]

    @property
    def nombre_archivo(self):
        return self.kwargs["modelo"]

    def filtrar(self, queryset, datos):
        lookups = self.recurso.get("lookups", {})
        rangos = self.recurso.get("ranges", {})
        for nombre, valor in datos.items():
            if valor in (None, ""):
                continue
            if nombre == "texto":
                busqueda = Q()
                for campo in self.recurso.get("texto", ()):
                    busqueda |= Q(**{f"{campo}__icontains": valor})
                queryset = queryset.filter(busqueda)
            elif nombre in lookups:
                if nombre == "periodo" and self.recurso["modelo"] is Profesor:
                    queryset = queryset.filter(secciones__periodo=valor).distinct()
                else:
                    queryset = queryset.filter(**{lookups[nombre]: valor})
            elif nombre in rangos:
                queryset = queryset.filter(**{rangos[nombre]: valor})
            elif nombre == "anio":
                queryset = queryset.filter(fecha_inicio__year=valor)
            elif nombre in self.recurso.get("date_ranges", {}):
                for lookup in self.recurso["date_ranges"][nombre]:
                    queryset = queryset.filter(**{lookup: valor})
        return queryset


class RecursoEscrituraMixin(RecursoMixin):
    def get_nota_formset(self, data=None, files=None):
        return NotaFormSet(
            data=data,
            files=files,
            instance=getattr(self, "object", None),
            prefix="nota",
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        if self.recurso["modelo"] is Matricula:
            contexto["nota_formset"] = kwargs.get("nota_formset") or self.get_nota_formset()
        return contexto

    def form_valid(self, form):
        with transaction.atomic():
            if self.recurso["modelo"] is Periodo and form.instance.activo:
                Periodo.objects.exclude(pk=form.instance.pk).update(activo=False)
            form.instance.user = self.request.user
            response = super().form_valid(form)
        return response

    def post(self, request, *args, **kwargs):
        if self.recurso["modelo"] is not Matricula:
            return super().post(request, *args, **kwargs)
        self.object = getattr(self, "object", None)
        if isinstance(self, UpdateView):
            self.object = self.get_object()
        form = self.get_form()
        nota_formset = self.get_nota_formset(request.POST, request.FILES)
        if form.is_valid() and nota_formset.is_valid():
            return self.guardar_matricula(form, nota_formset)
        return self.form_invalid(form, nota_formset=nota_formset)

    def form_invalid(self, form, nota_formset=None):
        contexto = self.get_context_data(
            form=form,
            nota_formset=nota_formset or self.get_nota_formset(self.request.POST, self.request.FILES),
        )
        return self.render_to_response(contexto)

    def guardar_matricula(self, form, nota_formset):
        try:
            with transaction.atomic():
                matricula = form.save(commit=False)
                matricula.user = self.request.user
                matricula.full_clean()
                matricula.save()
                form.save_m2m()
                nota_formset.instance = matricula
                for nota in nota_formset.save(commit=False):
                    nota.user = self.request.user
                    nota.save()
                nota_formset.save_m2m()
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form, nota_formset=nota_formset)
        self.object = matricula
        messages.success(self.request, "Matrícula y notas guardadas correctamente.")
        return redirect(self.get_success_url())


class RecursoCreateView(
    LoginRequiredMixin, UsuarioRegistroMixin, RecursoEscrituraMixin,
    SuccessMessageMixin, CreateView,
):
    template_name = "academico/formulario.html"
    success_message = "Registro creado correctamente."


class RecursoUpdateView(
    LoginRequiredMixin, UsuarioRegistroMixin, RecursoEscrituraMixin,
    SuccessMessageMixin, UpdateView,
):
    template_name = "academico/formulario.html"
    success_message = "Registro actualizado correctamente."


class RecursoDeleteView(LoginRequiredMixin, RecursoMixin, DeleteView):
    template_name = "academico/confirmar_eliminacion.html"

    def get_form_class(self):
        return forms.Form

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "No se puede eliminar porque existen registros relacionados.",
            )
            return redirect(self.get_success_url())
        messages.success(
            self.request,
            f"{self.recurso['modelo']._meta.verbose_name.capitalize()} eliminado correctamente.",
        )
        return response


class RecursoDetailView(LoginRequiredMixin, RecursoMixin, DetailView):
    template_name = "academico/detalle.html"
    context_object_name = "objeto"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        objeto = contexto["objeto"]
        columnas = self.recurso["columnas"]
        contexto.update({
            "modelo": self.kwargs["modelo"],
            "titulo": f"{self.recurso['modelo']._meta.verbose_name.capitalize()} · {objeto}",
            "datos": [
                (titulo, valor_campo(objeto, ruta))
                for ruta, titulo in columnas
                if ruta not in {"total_facultades", "inscritos"}
            ],
            "tablas_relacionadas": _tablas_relacionadas(self.recurso["modelo"], objeto),
        })
        return contexto


class RecursoPdfView(LoginRequiredMixin, ComprobantePdfMixin, RecursoMixin, DetailView):
    template_pdf = "academico/pdf/comprobante.html"
    template_name = "academico/pdf/comprobante.html"
    context_object_name = "objeto"

    def get_nombre_archivo(self):
        return self.kwargs["modelo"]

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        objeto = contexto["objeto"]
        modelo = self.kwargs["modelo"]
        recurso = self.recurso
        logo = self.get_logo(objeto)
        if modelo == "estudiantes":
            contexto["tablas_relacionadas"] = _tablas_relacionadas(Estudiante, objeto)
        else:
            contexto["tablas_relacionadas"] = _tablas_relacionadas(recurso["modelo"], objeto)
        contexto.update({
            "modelo": modelo,
            "titulo": {
                "estudiantes": "Ficha del estudiante",
                "matriculas": f"Comprobante de matrícula N.º {objeto.pk}",
                "profesores": "Carga académica",
                "secciones": "Acta de calificaciones",
                "carreras": "Malla curricular",
            }.get(modelo, f"Ficha de {recurso['modelo']._meta.verbose_name.lower()}"),
            "subtitulo": str(objeto),
            "datos": [
                (titulo, valor_campo(objeto, ruta))
                for ruta, titulo in recurso["columnas"]
                if ruta not in {"total_facultades", "inscritos"}
            ],
            "logo_url": logo.url if logo and logo.name else "",
            "registro": objeto,
        })
        if isinstance(objeto, Estudiante) and objeto.foto:
            contexto["foto_url"] = objeto.foto.url
        return contexto

    def get_logo(self, objeto):
        if isinstance(objeto, Universidad):
            return objeto.logo
        if isinstance(objeto, Facultad):
            return objeto.universidad.logo
        if isinstance(objeto, Carrera):
            return objeto.facultad.universidad.logo
        if isinstance(objeto, Estudiante):
            return objeto.carrera.facultad.universidad.logo
        if isinstance(objeto, Curso):
            return objeto.carrera.facultad.universidad.logo
        if isinstance(objeto, Semestre):
            curso = objeto.cursos.select_related("carrera__facultad__universidad").first()
            return curso.carrera.facultad.universidad.logo if curso else None
        if isinstance(objeto, Seccion):
            return objeto.curso.carrera.facultad.universidad.logo
        if isinstance(objeto, (Matricula, Nota)):
            matricula = objeto if isinstance(objeto, Matricula) else objeto.matricula
            return matricula.estudiante.carrera.facultad.universidad.logo
        if isinstance(objeto, Profesor):
            seccion = objeto.secciones.select_related("curso__carrera__facultad__universidad").first()
            return seccion.curso.carrera.facultad.universidad.logo if seccion else None
        if isinstance(objeto, Periodo):
            seccion = objeto.secciones.select_related("curso__carrera__facultad__universidad").first()
            return seccion.curso.carrera.facultad.universidad.logo if seccion else None
        return None


class InicioView(LoginRequiredMixin, ListView):
    template_name = "academico/inicio.html"
    model = Estudiante

    def get_queryset(self):
        return Estudiante.objects.all()

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        periodo_activo = Periodo.objects.filter(activo=True).first()
        notas = Nota.objects.filter(matricula__seccion__periodo=periodo_activo) if periodo_activo else Nota.objects.none()
        total_notas = notas.count()
        aprobados = notas.filter(estado=EstadoNota.APROBADO).count()
        contexto.update({
            "total_estudiantes": Estudiante.objects.count(),
            "periodo_activo": periodo_activo,
            "total_secciones": Seccion.objects.filter(periodo=periodo_activo).count() if periodo_activo else 0,
            "total_matriculas": Matricula.objects.filter(seccion__periodo=periodo_activo).count() if periodo_activo else 0,
            "total_aprobados": aprobados,
            "total_reprobados": total_notas - aprobados,
            "porcentaje_aprobados": round(aprobados * 100 / total_notas, 1) if total_notas else 0,
        })
        return contexto
