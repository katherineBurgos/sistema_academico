# =====================================================================
# academico/models.py · Sistema académico
# Orden: estructura (Universidad → Facultad → Carrera) → catálogo (Semestre, Periodo, Curso)
#        → personas (Profesor, Estudiante) → oferta (Seccion) → proceso (Matricula → Nota)
# =====================================================================
from decimal import Decimal
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import ModeloBase

NOTA_MINIMA_APROBACION = Decimal("70")           # regla del negocio: se aprueba con 70 o más
NOTA_MAXIMA = Decimal("100")
VALIDAR_NOTA = [MinValueValidator(Decimal("0")), MaxValueValidator(NOTA_MAXIMA)]   # 0 ≤ nota ≤ 100


# ---------------------------------------------------------------------
# OPCIONES FIJAS (choices)
# ---------------------------------------------------------------------
class Jornada(models.TextChoices):
    VESPERTINA = "vespertina", "Vespertino"
    NOCTURNA = "nocturna", "Nocturno"


class EstadoNota(models.TextChoices):
    APROBADO = "aprobado", "Aprobado"
    REPROBADO = "reprobado", "Reprobado"


# =====================================================================
# 1. ESTRUCTURA: Universidad 1:N Facultad 1:N Carrera
# =====================================================================
class Universidad(ModeloBase):
    nombre = models.CharField(max_length=150, unique=True)
    siglas = models.CharField(max_length=20)                         # Ej: UG, ESPOL
    ciudad = models.CharField(max_length=80)
    logo = models.ImageField(upload_to="universidades/", blank=True)  # sale en los comprobantes PDF

    class Meta:
        verbose_name = "Universidad"
        verbose_name_plural = "Universidades"
        ordering = ["nombre"]

    def __str__(self):
        return self.siglas

    @property
    def total_facultades(self):
        return self.facultades.count()


class Facultad(ModeloBase):
    universidad = models.ForeignKey(Universidad, on_delete=models.PROTECT, related_name="facultades")   # 1:N
    nombre = models.CharField(max_length=150)
    decano = models.CharField(max_length=150, blank=True)

    class Meta:
        verbose_name = "Facultad"
        verbose_name_plural = "Facultades"
        ordering = ["nombre"]
        constraints = [   # el mismo nombre puede existir en otra universidad, pero no dos veces en la misma
            models.UniqueConstraint(fields=["universidad", "nombre"], name="facultad_unica_por_universidad"),
        ]

    def __str__(self):
        return self.nombre


class Carrera(ModeloBase):
    facultad = models.ForeignKey(Facultad, on_delete=models.PROTECT, related_name="carreras")   # 1:N
    codigo = models.CharField("Código", max_length=10, unique=True)   # Ej: SOF
    nombre = models.CharField(max_length=150)
    duracion_semestres = models.PositiveSmallIntegerField("Duración (semestres)", default=8)

    class Meta:
        verbose_name = "Carrera"
        verbose_name_plural = "Carreras"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


# =====================================================================
# 2. CATÁLOGO: Semestre, Periodo y Curso
# =====================================================================
class Semestre(ModeloBase):
    numero = models.PositiveSmallIntegerField(unique=True, validators=[MinValueValidator(1), MaxValueValidator(12)])
    nombre = models.CharField(max_length=30)                          # Ej: Primer semestre

    class Meta:
        verbose_name = "Semestre"
        verbose_name_plural = "Semestres"
        ordering = ["numero"]

    def __str__(self):
        return self.nombre


class Periodo(ModeloBase):
    nombre = models.CharField(max_length=20, unique=True)             # Ej: 2026-1
    fecha_inicio = models.DateField("Fecha de inicio")
    fecha_fin = models.DateField("Fecha de fin")
    activo = models.BooleanField(default=False)                       # el periodo en el que se matricula

    class Meta:
        verbose_name = "Periodo"
        verbose_name_plural = "Periodos"
        ordering = ["-fecha_inicio"]                                  # el más reciente primero

    def __str__(self):
        return self.nombre

    def clean(self):                                                  # validación de VARIOS campos juntos
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin <= self.fecha_inicio:
            raise ValidationError({"fecha_fin": "La fecha de fin debe ser posterior a la de inicio."})


class Curso(ModeloBase):                                              # la asignatura (materia)
    carrera = models.ForeignKey(Carrera, on_delete=models.PROTECT, related_name="cursos")      # 1:N
    semestre = models.ForeignKey(Semestre, on_delete=models.PROTECT, related_name="cursos")    # 1:N
    codigo = models.CharField("Código", max_length=12, unique=True)  # Ej: SOF-101
    nombre = models.CharField(max_length=150)
    creditos = models.PositiveSmallIntegerField("Créditos", default=3)

    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"
        ordering = ["carrera", "semestre__numero", "nombre"]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"


# =====================================================================
# 3. PERSONAS: Profesor y Estudiante
# =====================================================================
class Profesor(ModeloBase):
    cedula = models.CharField("Cédula", max_length=10, unique=True)
    nombres = models.CharField(max_length=80)
    apellidos = models.CharField(max_length=80)
    email = models.EmailField("Correo", blank=True)
    titulo = models.CharField("Título", max_length=120, blank=True)  # Ej: Mg. en Software

    class Meta:
        verbose_name = "Profesor"
        verbose_name_plural = "Profesores"
        ordering = ["apellidos", "nombres"]

    def __str__(self):
        return f"{self.apellidos} {self.nombres}"


class Estudiante(ModeloBase):
    cedula = models.CharField("Cédula", max_length=10, unique=True)
    nombres = models.CharField(max_length=80)
    apellidos = models.CharField(max_length=80)
    email = models.EmailField("Correo", blank=True)
    telefono = models.CharField("Teléfono", max_length=15, blank=True)
    fecha_nacimiento = models.DateField("Fecha de nacimiento", null=True, blank=True)
    carrera = models.ForeignKey(Carrera, on_delete=models.PROTECT, related_name="estudiantes")   # 1:N
    cuenta = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perfil_estudiante",
        verbose_name="Cuenta de acceso",
    )
    foto = models.ImageField(upload_to="estudiantes/", blank=True)

    class Meta:
        verbose_name = "Estudiante"
        verbose_name_plural = "Estudiantes"
        ordering = ["apellidos", "nombres"]

    def __str__(self):
        return f"{self.apellidos} {self.nombres}"

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"


# =====================================================================
# 4. OFERTA: la Sección es UN curso, en UN periodo, con UN profesor, en UNA jornada
# =====================================================================
class Seccion(ModeloBase):
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT, related_name="secciones")
    periodo = models.ForeignKey(Periodo, on_delete=models.PROTECT, related_name="secciones")
    profesor = models.ForeignKey(Profesor, on_delete=models.PROTECT, related_name="secciones")
    paralelo = models.CharField(max_length=2, default="A")            # A, B, C...
    jornada = models.CharField(
        max_length=10,
        choices=Jornada.choices,
        default=Jornada.VESPERTINA,
    )
    cupo = models.PositiveSmallIntegerField(default=30)
    # N:M con Estudiante A TRAVÉS de Matricula (la tabla intermedia la escribimos nosotros: tiene datos propios)
    estudiantes = models.ManyToManyField("Estudiante", through="Matricula", related_name="secciones")

    class Meta:
        verbose_name = "Sección"
        verbose_name_plural = "Secciones"
        ordering = ["periodo", "curso", "paralelo"]
        constraints = [
            models.UniqueConstraint(fields=["curso", "periodo", "paralelo", "jornada"], name="seccion_unica"),
        ]

    def __str__(self):
        return f"{self.curso.codigo} {self.paralelo} · {self.get_jornada_display()} · {self.periodo}"

    @property
    def inscritos(self):
        return self.matriculas.count()

    @property
    def horario_resumen(self):
        bloques = [
            f"{horario} {horario.aula}".strip()
            for horario in self.horarios.all()
        ]
        return "; ".join(bloques) or "Sin horario asignado"

    def tiene_choque_horario(self, estudiante, matricula_id=None):
        otras_matriculas = Matricula.objects.filter(
            estudiante=estudiante,
            seccion__periodo_id=self.periodo_id,
        ).exclude(seccion_id=self.pk)
        if matricula_id:
            otras_matriculas = otras_matriculas.exclude(pk=matricula_id)
        otras_secciones = otras_matriculas.values_list("seccion_id", flat=True)
        horarios_actuales = HorarioSeccion.objects.filter(seccion_id__in=otras_secciones)
        for horario in self.horarios.all():
            if horarios_actuales.filter(
                dia=horario.dia,
                hora_inicio__lt=horario.hora_fin,
                hora_fin__gt=horario.hora_inicio,
            ).exists():
                return True
        return False


class DiaSemana(models.IntegerChoices):
    LUNES = 1, "Lunes"
    MARTES = 2, "Martes"
    MIERCOLES = 3, "Miércoles"
    JUEVES = 4, "Jueves"
    VIERNES = 5, "Viernes"
    SABADO = 6, "Sábado"
    DOMINGO = 7, "Domingo"


class HorarioSeccion(ModeloBase):
    seccion = models.ForeignKey(
        Seccion,
        on_delete=models.CASCADE,
        related_name="horarios",
    )
    dia = models.PositiveSmallIntegerField(choices=DiaSemana.choices)
    hora_inicio = models.TimeField("Hora de inicio")
    hora_fin = models.TimeField("Hora de fin")
    aula = models.CharField(max_length=80, blank=True)

    class Meta:
        verbose_name = "Horario de asignatura"
        verbose_name_plural = "Horarios de asignaturas"
        ordering = ["dia", "hora_inicio"]
        constraints = [
            models.UniqueConstraint(
                fields=["seccion", "dia", "hora_inicio"],
                name="horario_unico_por_seccion_dia_inicio",
            ),
        ]

    def __str__(self):
        return (
            f"{self.get_dia_display()} {self.hora_inicio:%H:%M}-"
            f"{self.hora_fin:%H:%M}"
        )

    def clean(self):
        if self.hora_inicio and self.hora_fin and self.hora_inicio >= self.hora_fin:
            raise ValidationError({
                "hora_fin": "La hora de fin debe ser posterior a la hora de inicio."
            })
        if not self.seccion_id or not self.dia or not self.hora_inicio or not self.hora_fin:
            return
        horarios_solapados = type(self).objects.filter(
            seccion_id=self.seccion_id,
            dia=self.dia,
            hora_inicio__lt=self.hora_fin,
            hora_fin__gt=self.hora_inicio,
        ).exclude(pk=self.pk)
        if horarios_solapados.exists():
            raise ValidationError("Los bloques de una sección no pueden superponerse.")


# =====================================================================
# 5. PROCESO: Matricula (N:M Estudiante–Seccion con datos) y Nota (1:1 con Matricula)
# =====================================================================
class Matricula(ModeloBase):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.PROTECT, related_name="matriculas")
    seccion = models.ForeignKey(Seccion, on_delete=models.PROTECT, related_name="matriculas")
    fecha = models.DateField(default=timezone.localdate)

    class Meta:
        verbose_name = "Matrícula"
        verbose_name_plural = "Matrículas"
        ordering = ["-fecha"]
        constraints = [   # un estudiante no se matricula dos veces en la misma sección
            models.UniqueConstraint(fields=["estudiante", "seccion"], name="matricula_unica"),
        ]

    def __str__(self):
        return f"{self.estudiante} → {self.seccion}"

    def clean(self):
        """Reglas del negocio que miran OTRAS tablas."""
        if not self.estudiante_id or not self.seccion_id:     # si falta alguno, ya lo avisa su propio campo
            return
        if self.seccion.curso.carrera_id != self.estudiante.carrera_id:
            raise ValidationError("El curso no pertenece a la carrera del estudiante.")
        ocupados = self.seccion.matriculas.exclude(pk=self.pk).count()
        if ocupados >= self.seccion.cupo:
            raise ValidationError(f"La sección no tiene cupo ({self.seccion.cupo} estudiantes).")
        if self.seccion.tiene_choque_horario(self.estudiante, self.pk):
            raise ValidationError({
                "seccion": "El horario se superpone con otra asignatura de este periodo."
            })


class Nota(ModeloBase):
    matricula = models.OneToOneField(Matricula, on_delete=models.CASCADE, related_name="nota")   # 1:1
    n1 = models.DecimalField("Nota 1", max_digits=5, decimal_places=2, default=0, validators=VALIDAR_NOTA)
    n2 = models.DecimalField("Nota 2", max_digits=5, decimal_places=2, default=0, validators=VALIDAR_NOTA)
    n3 = models.DecimalField("Nota 3", max_digits=5, decimal_places=2, default=0, validators=VALIDAR_NOTA)
    # Calculados en save(): se guardan para poder FILTRAR y EXPORTAR por ellos
    promedio = models.DecimalField(max_digits=5, decimal_places=2, default=0, editable=False)
    estado = models.CharField(max_length=10, choices=EstadoNota.choices, default=EstadoNota.REPROBADO, editable=False)

    class Meta:
        verbose_name = "Nota"
        verbose_name_plural = "Notas"

    def __str__(self):
        return f"{self.matricula.estudiante} · {self.promedio} ({self.get_estado_display()})"

    def save(self, *args, **kwargs):
        """Antes de guardar: calcula el promedio y decide si aprueba."""
        self.promedio = ((self.n1 + self.n2 + self.n3) / 3).quantize(Decimal("0.01"))
        self.estado = EstadoNota.APROBADO if self.promedio >= NOTA_MINIMA_APROBACION else EstadoNota.REPROBADO
        super().save(*args, **kwargs)                            # ahora sí: INSERT o UPDATE


class AsignacionTutoria(ModeloBase):
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.PROTECT,
        related_name="asignaciones_tutoria",
    )
    tutor = models.ForeignKey(
        Profesor,
        on_delete=models.PROTECT,
        related_name="asignaciones_tutoria",
    )
    fecha_inicio = models.DateField("Fecha de inicio", default=timezone.localdate)
    fecha_fin = models.DateField("Fecha de fin", null=True, blank=True)
    activa = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "Asignación de tutoría"
        verbose_name_plural = "Asignaciones de tutoría"
        ordering = ["-fecha_inicio", "estudiante"]
        constraints = [
            models.UniqueConstraint(
                fields=["estudiante"],
                condition=models.Q(activa=True),
                name="una_tutoria_activa_por_estudiante",
            ),
        ]

    def __str__(self):
        return f"{self.estudiante} · {self.tutor}"

    def clean(self):
        if self.fecha_fin and self.fecha_inicio and self.fecha_fin < self.fecha_inicio:
            raise ValidationError({
                "fecha_fin": "La fecha de fin no puede ser anterior a la fecha de inicio."
            })
        if self.activa and self.fecha_fin:
            raise ValidationError({
                "fecha_fin": "Una asignación activa no puede tener fecha de fin."
            })
        if self.activa and self.estudiante_id:
            asignaciones_activas = type(self).objects.filter(
                estudiante_id=self.estudiante_id,
                activa=True,
            ).exclude(pk=self.pk)
            if asignaciones_activas.exists():
                raise ValidationError({
                    "estudiante": "El estudiante ya tiene una asignación de tutoría activa."
                })


class EstadoSesionTutoria(models.TextChoices):
    PROGRAMADA = "programada", "Programada"
    REALIZADA = "realizada", "Realizada"
    CANCELADA = "cancelada", "Cancelada"


class ModalidadTutoria(models.TextChoices):
    PRESENCIAL = "presencial", "Presencial"
    VIRTUAL = "virtual", "Virtual"


class SesionTutoria(ModeloBase):
    asignacion = models.ForeignKey(
        AsignacionTutoria,
        on_delete=models.PROTECT,
        related_name="sesiones",
    )
    fecha = models.DateField(default=timezone.localdate)
    tema = models.CharField(max_length=150)
    modalidad = models.CharField(
        max_length=12,
        choices=ModalidadTutoria.choices,
        default=ModalidadTutoria.PRESENCIAL,
    )
    duracion_minutos = models.PositiveSmallIntegerField(
        "Duración (minutos)",
        default=60,
        validators=[MinValueValidator(15), MaxValueValidator(240)],
    )
    estado = models.CharField(
        max_length=12,
        choices=EstadoSesionTutoria.choices,
        default=EstadoSesionTutoria.PROGRAMADA,
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "Sesión de tutoría"
        verbose_name_plural = "Sesiones de tutoría"
        ordering = ["-fecha", "asignacion"]

    def __str__(self):
        return f"{self.fecha} · {self.asignacion.estudiante} · {self.tema}"

    def clean(self):
        if not self.asignacion_id or not self.fecha:
            return
        if self.fecha < self.asignacion.fecha_inicio:
            raise ValidationError({
                "fecha": "La sesión no puede ser anterior al inicio de la asignación."
            })
        if self.asignacion.fecha_fin and self.fecha > self.asignacion.fecha_fin:
            raise ValidationError({
                "fecha": "La sesión no puede ser posterior al fin de la asignación."
            })


class CertificadoAprobacion(ModeloBase):
    matricula = models.ForeignKey(
        Matricula,
        on_delete=models.PROTECT,
        related_name="certificados_aprobacion",
    )
    codigo = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    nombre_estudiante = models.CharField(max_length=161)
    cedula_estudiante = models.CharField(max_length=10)
    curso = models.CharField(max_length=200)
    periodo = models.CharField(max_length=30)
    promedio = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=VALIDAR_NOTA,
    )
    fecha_emision = models.DateTimeField(default=timezone.now)
    qr = models.ImageField(upload_to="certificados/qr/", blank=True)

    class Meta:
        verbose_name = "Certificado de aprobación"
        verbose_name_plural = "Certificados de aprobación"
        ordering = ["-fecha_emision"]
        constraints = [
            models.UniqueConstraint(
                fields=["matricula", "promedio"],
                name="certificado_unico_por_matricula_y_promedio",
            ),
        ]

    def __str__(self):
        return f"Certificado {self.codigo} · {self.nombre_estudiante}"
