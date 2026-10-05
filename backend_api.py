import os
import secrets
from datetime import date, datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field
from pymongo import MongoClient

load_dotenv()

# Configuración

INTERNAL_GATEWAY_SECRET = os.getenv("INTERNAL_GATEWAY_SECRET")
if not INTERNAL_GATEWAY_SECRET:
    raise RuntimeError("INTERNAL_GATEWAY_SECRET no está configurado")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "flor_vida")

app = FastAPI(
    title="Flor & Vida — API de negocio",
    description="Expone productos y pedidos. Solo debe ser llamada por el API Gateway.",
)

mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB_NAME]
productos_col = db["productos"]
pedidos_col = db["pedidos"]

# Catálogo inicial
PRODUCTOS_INICIALES = [
    {"id": "ramo-aurora", "nombre": "Ramo Aurora", "categoria": "ramos", "precio": 18990,
     "descripcion": "Rosas y ranúnculos en tonos coral, atados con lino natural.",
     "imagen": "img/ramo-aurora.jpg"},
    {"id": "ramo-silvestre", "nombre": "Ramo Silvestre", "categoria": "ramos", "precio": 15990,
     "descripcion": "Flores de campo mixtas, estilo libre y espontáneo.", "imagen": None},
    {"id": "ramo-vida-nueva", "nombre": "Ramo Vida Nueva", "categoria": "ramos", "precio": 21990,
     "descripcion": "Ideal para nacimientos y nuevos comienzos.", "imagen": None},
    {"id": "caja-terracota", "nombre": "Caja Terracota", "categoria": "cajas", "precio": 24990,
     "descripcion": "Arreglo compacto presentado en cerámica artesanal.", "imagen": None},
    {"id": "caja-atardecer", "nombre": "Caja Atardecer", "categoria": "cajas", "precio": 27990,
     "descripcion": "Girasoles y flores naranjas en caja de madera clara.", "imagen": None},
    {"id": "centro-boda-clasica", "nombre": "Centro de Mesa Boda Clásica", "categoria": "bodas", "precio": 45990,
     "descripcion": "Centro de mesa en tonos blancos y verdes para recepciones.", "imagen": None},
    {"id": "arco-ceremonia", "nombre": "Arco Floral Ceremonia", "categoria": "bodas", "precio": 189990,
     "descripcion": "Arco decorativo completo para ceremonias al aire libre.", "imagen": None},
    {"id": "suculenta-maceta", "nombre": "Suculenta en Maceta", "categoria": "plantas", "precio": 9990,
     "descripcion": "Suculenta de bajo cuidado en maceta de cerámica.", "imagen": None},
    {"id": "orquidea-phalaenopsis", "nombre": "Orquídea Phalaenopsis", "categoria": "plantas", "precio": 32990,
     "descripcion": "Orquídea blanca en maceta decorativa, larga floración.", "imagen": None},
]


@app.on_event("startup")
def seed_productos():
    """Si la colección 'productos' está vacía, la llena con el catálogo inicial."""
    if productos_col.count_documents({}) == 0:
        productos_col.insert_many([p.copy() for p in PRODUCTOS_INICIALES])


# Seguridad: solo el Gateway puede llamar a estos endpoints
def verify_gateway(x_gateway_secret: str = Header(default="")):
    valido = secrets.compare_digest(x_gateway_secret, INTERNAL_GATEWAY_SECRET)
    if not valido:
        raise HTTPException(status_code=403, detail="Solicitud no autorizada desde Gateway")


# Esquemas (Pydantic) — describen la forma de los datos

class Producto(BaseModel):
    id: str
    nombre: str
    categoria: str
    precio: int
    descripcion: str
    imagen: Optional[str] = None


class PedidoIn(BaseModel):
    nombre: str = Field(min_length=3)
    email: EmailStr
    telefono: str
    producto: str
    fecha: date
    direccion: str = Field(min_length=6)
    mensaje: Optional[str] = None


class PedidoOut(PedidoIn):
    numero_pedido: str
    estado: str
    creado_en: datetime


# Endpoints
@app.get("/health")
def health():
    return {"status": "OK", "service": "Flor & Vida — Backend API"}


@app.get("/productos", response_model=list[Producto], dependencies=[Depends(verify_gateway)])
def listar_productos():
    return list(productos_col.find({}, {"_id": 0}))


@app.post("/pedidos", response_model=PedidoOut, dependencies=[Depends(verify_gateway)])
def crear_pedido(pedido: PedidoIn, x_authenticated_client: Optional[str] = Header(default=None)):
    numero_pedido = f"FV-{datetime.now().year}-{secrets.randbelow(9000) + 1000}"

    documento = pedido.model_dump()
    documento["fecha"] = pedido.fecha.isoformat()  # Mongo no acepta 'date', solo 'datetime' o texto
    documento.update({
        "numero_pedido": numero_pedido,
        "estado": "recibido",
        "creado_en": datetime.utcnow(),
        "cliente_autenticado": x_authenticated_client,
    })

    pedidos_col.insert_one(documento)  # insert_one agrega la clave "_id" al mismo dict
    documento.pop("_id", None)
    return documento


@app.get("/pedidos/{numero_pedido}", response_model=PedidoOut, dependencies=[Depends(verify_gateway)])
def obtener_pedido(numero_pedido: str):
    pedido = pedidos_col.find_one({"numero_pedido": numero_pedido}, {"_id": 0})
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return pedido
