from fastapi import FastAPI

from app.routers import reservations

app = FastAPI(title="Hotel Reservations")
app.include_router(reservations.router)


@app.get("/health")
def health():
    return {"status": "ok"}
