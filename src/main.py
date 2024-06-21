from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tortoise import Tortoise
from src.database.register import register_tortoise
from src.database.config import TORTOISE_ORM
from src.routes import users, weatherapis, mcda
from src.crud import results

Tortoise.init_models(["src.database.models"], "models")

app = FastAPI()

# NEW
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(users.router)
app.include_router(weatherapis.router)
app.include_router(mcda.router)
register_tortoise(app, config=TORTOISE_ORM, generate_schemas=True)

@app.get("/")
def home():
    return {"message": "Hello World"}

