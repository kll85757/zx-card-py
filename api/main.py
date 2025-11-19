from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import router
from .constants import load_constants_from_readme

app = FastAPI(title="ZX Card Search API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/constants")
def get_constants():
    return load_constants_from_readme()


app.include_router(router, prefix="/api")


