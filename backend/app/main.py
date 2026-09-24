from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import admin, auth, quiz

app = FastAPI(title="Quiz Dr API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(quiz.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
