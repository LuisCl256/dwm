from fastapi import FastAPI

app = FastAPI(title="Backend API español")


@app.get("/salud")
def health():
    return {
        "status": "OK",
        "service": "Backend API"
    }


@app.get("/productos")
def productos():
    return {
        "productos": [
            {"id": 1, "nombre": "Notebook", "precio": 900000},
            {"id": 1, "nombre": "Monitor", "precio": 250000}
        ]
    }


@app.get("/orders")
def ordenes():
    return {
        "ordenes": [
            {"id": 1001, "estado": "pagado"},
            {"id": 1002, "estado": "pendiente"}
        ]
    }
