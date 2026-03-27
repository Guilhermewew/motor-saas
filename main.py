from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
from pydantic import BaseModel
import mercadopago

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

URL_SUPABASE = "https://sdffwrpacvtjncuqtrft.supabase.co"
CHAVE_SUPABASE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNkZmZ3cnBhY3Z0am5jdXF0cmZ0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ1NjU3NTAsImV4cCI6MjA5MDE0MTc1MH0.FarfM9aF-rKZOqEfhzt6Oqar1aN3H75wkHoySMAICcg"
banco = create_client(URL_SUPABASE, CHAVE_SUPABASE)

class NovoProduto(BaseModel):
    nome: str
    preco: float
    foto_url: str
    loja_id: str
    user_id: str # ID do dono da loja

@app.get("/produtos")
def pegar_produtos(user_id: str = None):
    query = banco.table("produtos").select("*")
    if user_id:
        query = query.eq("user_id", user_id) # Só mostra o que é do dono
    resposta = query.execute()
    return resposta.data

@app.post("/produtos")
def criar_produto(item: NovoProduto):
    resposta = banco.table("produtos").insert({
        "nome": item.nome, 
        "preco": item.preco, 
        "foto_url": item.foto_url, 
        "loja_id": item.loja_id,
        "user_id": item.user_id
    }).execute()
    return {"status": "ok", "dados": resposta.data}

# Mantém a rota de checkout e lojas igual...