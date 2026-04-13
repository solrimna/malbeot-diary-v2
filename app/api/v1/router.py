from fastapi import APIRouter

from app.api.v1 import alarm, auth, diary, feedback, persona, search, user, voice

api_router = APIRouter()

api_router.include_router(auth.router,     prefix="/auth",     tags=["Auth"])
api_router.include_router(user.router,     prefix="/users",    tags=["User"])
api_router.include_router(diary.router,    prefix="/diaries",  tags=["Diary"])       
api_router.include_router(persona.router,  prefix="/personas", tags=["Persona"])     
api_router.include_router(feedback.router, prefix="/feedback", tags=["AI Feedback"]) 
api_router.include_router(voice.router,    prefix="/voice",    tags=["Voice"])       
api_router.include_router(alarm.router,    prefix="/alarms",   tags=["Alarm"])       
api_router.include_router(search.router,   prefix="/search",   tags=["AI Search"])
