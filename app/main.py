from fastapi import FastAPI

from app.routers import availability, reservations

app = FastAPI(title="Hotel Reservations")
app.include_router(reservations.router)
app.include_router(availability.router)


@app.get("/health")
def health():
    return {"status": "ok"}
