from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import review

app = FastAPI(title="PR Review Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(review.router)
