from fastapi import APIRouter, Depends,Request,HTTPException, status, Form
from sqlalchemy.orm import Session
from app.database import SessionLocal, get_db
from app import models, schemas
from typing import List
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials, OAuth2PasswordBearer
import secrets
from starlette.status import HTTP_303_SEE_OTHER
import os
from fastapi.templating import Jinja2Templates


templates = Jinja2Templates(directory="app/templates")



security = OAuth2PasswordBearer(tokenUrl="token")
router = APIRouter()

# Usuario y clave para admin (puedes usar variables de entorno)
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "1234")

# Variable simple para sesión (en producción usar OAuth o JWT)
admin_sessions = set()

@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})

@router.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USER and password == ADMIN_PASS:
        response = RedirectResponse(url="/admin/panel", status_code=HTTP_303_SEE_OTHER)
        # Guarda la sesión en cookie (básico, no seguro)
        response.set_cookie(key="admin_session", value="valid")
        return response
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Credenciales inválidas"})

def verificar_login(request: Request):
    cookie = request.cookies.get("admin_session")
    if cookie != "valid":
        raise RedirectResponse(url="/admin/login")

@router.get("/panel", response_class=HTMLResponse)
def panel(request: Request, db: Session = Depends(get_db)):
    try:
        verificar_login(request)
    except RedirectResponse as redirect:
        return redirect

    mantenciones = db.query(models.Agendamiento).all()
    return templates.TemplateResponse("admin_panel.html", {"request": request, "mantenciones": mantenciones})

@router.post("/eliminar/{id}")
def eliminar_agendamiento(id: int, db: Session = Depends(get_db),
                          credentials: HTTPBasicCredentials = Depends(verificar_login)):
    agendamiento = db.query(models.Agendamiento).get(id)
    if not agendamiento:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(agendamiento)
    db.commit()
    return RedirectResponse("/admin/panel", status_code=303)

def verificar_login(credentials: HTTPBasicCredentials = Depends(security)):
    usuario_valido = "admin"
    contraseña_valida = "1234"  # puedes cambiarla o usar env vars

    correcto = secrets.compare_digest(credentials.username, usuario_valido) and \
               secrets.compare_digest(credentials.password, contraseña_valida)
    if not correcto:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Basic"},
        )
    
@router.get("/panel", response_class=HTMLResponse)
def panel_agendamientos(
    request: Request,
    db: Session = Depends(get_db),
    credentials: HTTPBasicCredentials = Depends(verificar_login)
):
    agendamientos = db.query(models.Agendamiento).order_by(models.Agendamiento.fecha_inicio).all()
    return templates.TemplateResponse("admin_agendamientos.html", {
        "request": request,
        "agendamientos": agendamientos
    })

# Dependency para obtener sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/agendamientos", response_model=List[schemas.AgendamientoOut])

def listar_agendamientos(db: Session = Depends(get_db)):
    return db.query(models.Agendamiento).order_by(models.Agendamiento.fecha_inicio).all()


@router.get("/panel", response_class=HTMLResponse)
def panel_agendamientos(request: Request, db: Session = Depends(get_db)):
    agendamientos = db.query(models.Agendamiento).order_by(models.Agendamiento.fecha_inicio).all()
    return templates.TemplateResponse("admin_agendamientos.html", {
        "request": request,
        "agendamientos": agendamientos
    })