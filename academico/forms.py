from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import inlineformset_factory, modelform_factory

from .models import (
    AsignacionTutoria, Carrera, Curso, EstadoNota, Estudiante,
    Facultad, HorarioSeccion, Jornada, Matricula, Nota, Periodo, Profesor,
    Seccion, Semestre, SesionTutoria, Universidad,
)


def _cedula_valida(valor):
    if not valor.isdigit() or len(valor) != 10:
        raise ValidationError("La cédula debe tener exactamente 10 números.")
    return valor


class EstudianteForm(forms.ModelForm):
    class Meta:
        model = Estudiante
        fields = (
            "cedula", "nombres", "apellidos", "email", "telefono",
            "fecha_nacimiento", "carrera", "foto",
        )
        widgets = {
            "fecha_nacimiento": forms.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d",
            ),
        }

    def clean_cedula(self):
        return _cedula_valida(self.cleaned_data["cedula"])


class ProfesorForm(forms.ModelForm):
    class Meta:
        model = Profesor
        fields = ("cedula", "nombres", "apellidos", "email", "titulo")

    def clean_cedula(self):
        return _cedula_valida(self.cleaned_data["cedula"])


class CarreraForm(forms.ModelForm):
    class Meta:
        model = Carrera
        fields = ("facultad", "codigo", "nombre", "duracion_semestres")

    def clean_codigo(self):
        return self.cleaned_data["codigo"].strip().upper()


class AsignacionTutoriaForm(forms.ModelForm):
    class Meta:
        model = AsignacionTutoria
        fields = (
            "estudiante", "tutor", "fecha_inicio", "fecha_fin", "activa",
            "observaciones",
        )
        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date"}),
        }


class SesionTutoriaForm(forms.ModelForm):
    class Meta:
        model = SesionTutoria
        fields = (
            "asignacion", "fecha", "tema", "modalidad", "duracion_minutos",
            "estado", "observaciones",
        )
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"})}


class HorarioSeccionForm(forms.ModelForm):
    class Meta:
        model = HorarioSeccion
        fields = ("seccion", "dia", "hora_inicio", "hora_fin", "aula")
        widgets = {
            "hora_inicio": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "hora_fin": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        }


class SeccionConCupoField(forms.ModelChoiceField):
    def label_from_instance(self, seccion):
        bloques = []
        for horario in seccion.horarios.all():
            bloque = (
                f"{horario.get_dia_display()} "
                f"{horario.hora_inicio:%H:%M}-{horario.hora_fin:%H:%M}"
            )
            if horario.aula:
                bloque += f" · {horario.aula}"
            bloques.append(bloque)
        texto_horario = "; ".join(bloques) or "Sin horario asignado"
        return f"{seccion} · {texto_horario} ({seccion.inscritos}/{seccion.cupo})"


class MatriculaForm(forms.ModelForm):
    seccion = SeccionConCupoField(
        queryset=Seccion.objects.none(),
        label="Sección (inscritos/cupo)",
    )

    class Meta:
        model = Matricula
        fields = ("estudiante", "seccion", "fecha")
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        secciones = Seccion.objects.filter(periodo__activo=True)
        if self.instance and self.instance.pk:
            secciones = Seccion.objects.filter(
                Q(periodo__activo=True) | Q(pk=self.instance.seccion_id)
            )
        self.fields["seccion"].queryset = secciones.select_related(
            "curso", "periodo", "profesor"
        ).prefetch_related("horarios")


NOTA_WIDGETS = {
    nombre: forms.NumberInput(attrs={"min": "0", "max": "100", "step": "0.01"})
    for nombre in ("n1", "n2", "n3")
}

NotaFormSet = inlineformset_factory(
    Matricula,
    Nota,
    fields=("n1", "n2", "n3"),
    widgets=NOTA_WIDGETS,
    extra=1,
    max_num=1,
    can_delete=False,
)


class FiltroRecursoForm(forms.Form):
    texto = forms.CharField(label="Texto", required=False)
    ciudad = forms.CharField(label="Ciudad", required=False)
    universidad = forms.ModelChoiceField(
        label="Universidad", required=False, queryset=Universidad.objects.none(),
    )
    facultad = forms.ModelChoiceField(
        label="Facultad", required=False, queryset=Facultad.objects.none(),
    )
    carrera = forms.ModelChoiceField(
        label="Carrera", required=False, queryset=Carrera.objects.none(),
    )
    semestre = forms.ModelChoiceField(
        label="Semestre", required=False, queryset=Semestre.objects.none(),
    )
    periodo = forms.ModelChoiceField(
        label="Periodo", required=False, queryset=Periodo.objects.none(),
    )
    curso = forms.ModelChoiceField(
        label="Curso", required=False, queryset=Curso.objects.none(),
    )
    profesor = forms.ModelChoiceField(
        label="Profesor", required=False, queryset=Profesor.objects.none(),
    )
    jornada = forms.ChoiceField(
        label="Jornada",
        required=False,
        choices=(("", "Todas"), *Jornada.choices),
    )
    estado = forms.ChoiceField(
        label="Estado",
        required=False,
        choices=(("", "Todos"), *EstadoNota.choices),
    )
    activo = forms.ChoiceField(
        label="Activo",
        required=False,
        choices=(("", "Todos"), ("true", "Sí"), ("false", "No")),
    )
    anio = forms.IntegerField(
        label="Año", required=False, min_value=1900, max_value=2200,
    )
    promedio_desde = forms.DecimalField(
        label="Promedio desde", required=False, min_value=0, max_value=100,
    )
    promedio_hasta = forms.DecimalField(
        label="Promedio hasta", required=False, min_value=0, max_value=100,
    )
    nacido_desde = forms.DateField(
        label="Nacido desde",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    nacido_hasta = forms.DateField(
        label="Nacido hasta",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, campos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["universidad"].queryset = Universidad.objects.order_by("nombre")
        self.fields["facultad"].queryset = Facultad.objects.order_by("nombre")
        self.fields["carrera"].queryset = Carrera.objects.order_by("nombre")
        self.fields["semestre"].queryset = Semestre.objects.order_by("numero")
        self.fields["periodo"].queryset = Periodo.objects.order_by("-fecha_inicio")
        self.fields["curso"].queryset = Curso.objects.order_by("nombre")
        self.fields["profesor"].queryset = Profesor.objects.order_by("apellidos", "nombres")
        for campo in self.fields.values():
            campo.widget.attrs["class"] = (
                "form-select" if isinstance(campo.widget, forms.Select) else "form-control"
            )
        if campos is not None:
            for nombre in set(self.fields) - set(campos):
                self.fields.pop(nombre)

    def clean(self):
        datos = super().clean()
        if datos.get("promedio_desde") is not None and datos.get("promedio_hasta") is not None:
            if datos["promedio_desde"] > datos["promedio_hasta"]:
                self.add_error("promedio_hasta", "Debe ser igual o mayor al promedio inicial.")
        if datos.get("nacido_desde") and datos.get("nacido_hasta"):
            if datos["nacido_desde"] > datos["nacido_hasta"]:
                self.add_error("nacido_hasta", "Debe ser posterior a la fecha inicial.")
        return datos


def formulario_modelo(modelo, campos, widgets=None):
    return modelform_factory(
        modelo,
        fields=campos,
        widgets=widgets or {},
    )
