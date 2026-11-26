# Sistema Académico

Aplicación Django para administrar la estructura universitaria, estudiantes, profesores, periodos, cursos, secciones, matrículas y notas. Incluye registro e inicio de sesión, operaciones CRUD y un panel con el resumen académico.

El comando `poblar_datos` crea datos de demostración: 7 estudiantes, 7 secciones activas, 7 matrículas, 7 notas aprobadas y sus horarios de ejemplo.

## Tutorías y horarios

El menú **Tutorías** permite asignar un tutor a estudiantes y registrar sesiones con fecha, tema, modalidad y estado. Un estudiante puede tener una sola asignación activa a la vez.

Las secciones se ofrecen en jornadas **Vespertino** y **Nocturno**. Desde **Académico → Horarios de asignaturas**, los administradores pueden registrar varios bloques semanales por sección; cada bloque incluye día, hora de inicio y fin, y aula. Las matrículas se gestionan desde **Académico → Matrículas**.

Las notas se expresan de 0 a 100; el promedio se calcula con tres parciales y se aprueba con 70 o más.

## Gestión y reportes

Los módulos académicos incluyen listas paginadas, filtros, selección segura de columnas, exportación a Excel y reportes PDF. Cada registro dispone de una vista de detalle y, cuando aplica, un comprobante PDF con sus datos relacionados. Las validaciones del modelo protegen cupos, periodos y relaciones existentes.

## Ejecución local

En Windows, desde esta carpeta:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py poblar_datos
python manage.py runserver
```

Abre <http://127.0.0.1:8000/>. También puedes crear una cuenta desde la opción de registro o crear un usuario administrador con `python manage.py createsuperuser`.

## Configuración de seguridad

En desarrollo, Django genera una clave temporal si `DJANGO_SECRET_KEY` no está definida. Para cualquier entorno con `DJANGO_DEBUG=False`, configura una clave privada en `DJANGO_SECRET_KEY`. No guardes claves ni archivos `.env` en el repositorio.
