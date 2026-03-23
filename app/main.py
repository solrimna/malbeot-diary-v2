from fastapi import FastAPI
from app.database import Base, engine
from app.models import alarm
from app.services.alarm_scheduler import start_scheduler, stop_scheduler
from app.api.v1.alarm import router as alarms_router

app = FastAPI()

app.include_router(alarms_router)


@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    start_scheduler()


@app.on_event("shutdown")
async def on_shutdown():
    stop_scheduler()


@app.get("/")
async def root():
    return {"message": "ok"}