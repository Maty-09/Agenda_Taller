from fastapi import APIRouter, HTTPException, Depends,Request, Form, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.database import SessionLocal
from app import models, schemas
from app.utils.disponibilidad import verificar_disponibilidad
from app.utils.email_utils import enviar_correo_confirmacion
from fastapi import HTTPException
from app.crud import verificar_disponibilidad_especializado,verificar_disponibilidad
from app import models


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/agendar_web", response_class=HTMLResponse)
def mostrar_formulario(request: Request, tipo: str = None):
    return templates.TemplateResponse("agendar.html", {
        "request": request,
        "tipo_servicio": tipo        
    })


@router.post("/agendar_web", response_class=HTMLResponse)
def recibir_formulario(
    request: Request,
    tipo_servicio: str = Form(...),
    nombre: str = Form(...),
    apellido: str = Form(...),
    correo: str = Form(...),
    telefono: str = Form(...),
    patente: str = Form(...),
    fecha_inicio: str = Form(...),
    fecha_termino: str = Form(...),
    db: Session = Depends(get_db)
):

    try:
        # Convertir strings a datetime
        fecha_inicio_dt = datetime.fromisoformat(fecha_inicio)
        fecha_termino_dt = datetime.fromisoformat(fecha_termino)
    except ValueError:
        return templates.TemplateResponse("agendar.html", {
            "request": request,
            "error": "Formato de fecha/hora inválido.",
        })

    # Calcular duración en horas
    duracion = (fecha_termino_dt - fecha_inicio_dt).total_seconds() / 3600

    datos = schemas.AgendamientoCreate(
        tipo_servicio=tipo_servicio,
        nombre=nombre,
        apellido=apellido,
        correo=correo,
        telefono=telefono,
        patente=patente,
        fecha_inicio=fecha_inicio_dt,
        fecha_termino=fecha_termino_dt,
        duracion_horas=duracion
    )

    # Verificar disponibilidad
    disponible = verificar_disponibilidad(db, datos.tipo_servicio, datos.fecha_inicio, datos.duracion_horas)
    if not disponible:
        return templates.TemplateResponse("agendar.html", {
            "request": request,
            "error": "El horario solicitado no está disponible.",
            # También puedes pasar los datos para no hacer reingresar el formulario
            "datos": datos,
        })

    # Guardar en la base de datos
    nuevo = models.Agendamiento(**datos.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    # Enviar correo de confirmación
    asunto = "Confirmación de Mantención"
    contenido = f"""
    Hola {datos.nombre},
    Tu mantención fue agendada con éxito:

    🧾 Tipo de servicio: {datos.tipo_servicio}
    🕒 Inicio: {datos.fecha_inicio.strftime('%d-%m-%Y %H:%M')}
    ⏱️ Término: {datos.fecha_termino.strftime('%H:%M')}
    🚗 Patente: {datos.patente}

    ¡Gracias por confiar en nosotros!
    """
    enviar_correo_confirmacion(datos.correo, asunto, contenido)

    # Retornar plantilla con mensaje de éxito y formulario limpio
    return templates.TemplateResponse("agendar.html", {
        "request": request,
        "success": "¡Mantención agendada con éxito!",
    })


    


def verificar_disponibilidad(db: Session, tipo_servicio: str, inicio: datetime, duracion_horas: int) -> bool:
    fin = inicio + timedelta(hours=duracion_horas)

    if tipo_servicio == "especializado":
        # Validar horario laboral
        if not (8 <= inicio.hour < 16 and fin.hour <= 16):
            return False

        # Evitar hora de colación (12:00 a 13:00)
        colacion_inicio = inicio.replace(hour=12, minute=0)
        colacion_fin = inicio.replace(hour=13, minute=0)
        if inicio < colacion_fin and fin > colacion_inicio:
            return False

    elif tipo_servicio in ["taller", "domicilio"]:
        # Validar que sea una hora permitida
        hora_inicio_permitida = inicio.strftime("%H:%M")
        if hora_inicio_permitida not in ["09:00", "13:00", "15:30"]:
            return False

        if duracion_horas != 2:
            return False

    else:
        return False  # tipo no reconocido

    # Validar traslapes para cualquier tipo
    agendados = db.query(models.Agendamiento).filter(
        models.Agendamiento.tipo_servicio == tipo_servicio,
        models.Agendamiento.fecha_inicio < fin,
        models.Agendamiento.fecha_termino > inicio
    ).all()

    return len(agendados) == 0

    # Preparar el correo
    asunto = "Confirmación de Mantención"
    contenido = f"""
    Hola {datos.nombre},

    Tu mantención fue agendada con éxito:

    🧾 Tipo de servicio: {datos.tipo_servicio}
    🕒 Inicio: {datos.fecha_inicio.strftime('%d-%m-%Y %H:%M')}
    ⏱️ Término: {datos.fecha_termino.strftime('%H:%M')}
    🚗 Patente: {datos.patente}

    ¡Gracias por confiar en nosotros!
    """

    # Enviar el correo
    enviar_correo_confirmacion(datos.correo, asunto, contenido)

    return templates.TemplateResponse("agendar.html", {
        "request": request,
        "success": "¡Mantención agendada con éxito!"
    # No pasamos los campos para que el formulario quede vacío
    })


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/agendar", response_model=schemas.AgendamientoOut)
def agendar_cita(agendamiento: schemas.AgendamientoCreate, db: Session = Depends(get_db)):
    # Verificar disponibilidad
    print(">>> Entrando a /agendar")
    disponible = verificar_disponibilidad(db, agendamiento)

    if not disponible:
        raise HTTPException(status_code=400, detail="El horario solicitado no está disponible")

    # Crear agendamiento
    nuevo = models.Agendamiento(**agendamiento.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo
