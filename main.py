from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
from pydantic import BaseModel
import mercadopago

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

URL_SUPABASE = "https://sdffwrpacvtjncuqtrft.supabase.co"
CHAVE_SUPABASE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNkZmZ3cnBhY3Z0am5jdXF0cmZ0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ1NjU3NTAsImV4cCI6MjA5MDE0MTc1MH0.FarfM9aF-rKZOqEfhzt6Oqar1aN3H75wkHoySMAICcg"
banco = create_client(URL_SUPABASE, CHAVE_SUPABASE)

# --- REGRAS DE DADOS (Modelos) ---
class NovoPedido(BaseModel):
    titulo_produto: str
    preco: float

class NovoProduto(BaseModel):
    nome: str
    preco: float
    foto_url: str
    loja_id: str

# --- ROTAS DE LOJAS ---
@app.get("/lojas")
def pegar_lojas():
    resposta = banco.table("lojas").select("*").execute()
    return resposta.data

# --- ROTAS DE PRODUTOS ---
@app.get("/produtos")
def pegar_produtos():
    resposta = banco.table("produtos").select("*").execute()
    return resposta.data

@app.post("/produtos")
def criar_produto(item: NovoProduto):
    resposta = banco.table("produtos").insert({
        "nome": item.nome, 
        "preco": item.preco, 
        "foto_url": item.foto_url, 
        "loja_id": item.loja_id
    }).execute()
    return {"mensagem": "Produto salvo!", "dados": resposta.data}

# --- PAGAMENTO ---
TOKEN_MP = "TEST-7623525379052412-032620-4605c07246d1051aab714eb92804a977-331454528"
sdk = mercadopago.SDK(TOKEN_MP)

@app.post("/checkout")
def criar_pagamento(pedido: NovoPedido):
    dados_pagamento = {
        "items": [{"title": pedido.titulo_produto, "quantity": 1, "unit_price": pedido.preco}],
        "marketplace_fee": 5.00 
    }
    resposta_mp = sdk.preference().create(dados_pagamento)
    return {"link_de_pagamento": resposta_mp["response"]["init_point"]}