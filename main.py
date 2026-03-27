from fastapi import FastAPI
from supabase import create_client
from pydantic import BaseModel
import mercadopago

# 1. Criamos o nosso garçom
app = FastAPI()

# 2. Mostramos a ele onde fica a cozinha 
# (Você pega esses dados no painel do Supabase > Project Settings > API)
URL_SUPABASE = "https://sdffwrpacvtjncuqtrft.supabase.co"
CHAVE_SUPABASE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNkZmZ3cnBhY3Z0am5jdXF0cmZ0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ1NjU3NTAsImV4cCI6MjA5MDE0MTc1MH0.FarfM9aF-rKZOqEfhzt6Oqar1aN3H75wkHoySMAICcg"
banco = create_client(URL_SUPABASE, CHAVE_SUPABASE)

# 3. Ensinamos o garçom a buscar a lista de lojas
@app.get("/lojas")
def pegar_lojas():
    resposta = banco.table("lojas").select("*").execute()
    return resposta.data

# 4. Criamos uma regra de como a loja deve ser
class NovaLoja(BaseModel):
    nome: str
    slug: str

# 5. Ensinamos o garçom a guardar a loja no banco de dados
@app.post("/lojas")
def criar_loja(loja: NovaLoja):
    resposta = banco.table("lojas").insert({"nome": loja.nome, "slug": loja.slug}).execute()
    return resposta.data

# Configure com o seu Access Token de TESTE do Mercado Pago
TOKEN_MP = "TEST-7623525379052412-032620-4605c07246d1051aab714eb92804a977-331454528"
sdk = mercadopago.SDK(TOKEN_MP)

# Criamos a regra do que vem no pedido
class NovoPedido(BaseModel):
    titulo_produto: str
    preco: float

# Rota que gera o link de pagamento
@app.post("/checkout")
def criar_pagamento(pedido: NovoPedido):
    # Montamos o carrinho
    dados_pagamento = {
        "items": [
            {
                "title": pedido.titulo_produto,
                "quantity": 1,
                "unit_price": pedido.preco,
            }
        ],
        # A MÁGICA DO SPLIT: A sua comissão fixa
        "marketplace_fee": 5.00  # R$ 5,00 ficam para você, o resto vai direto para o vendedor
    }

    # Pede pro Mercado Pago criar o link
    resposta_mp = sdk.preference().create(dados_pagamento)
    
    # Entregamos o link final
    return {"link_de_pagamento": resposta_mp["response"]["init_point"]}
    # Pedimos pro Mercado Pago criar o link
    resposta_mp = sdk.preference().create(dados_pagamento)
    
    # Entregamos o link final (init_point) de volta
    return {"link_de_pagamento": resposta_mp["response"]["init_point"]}

class NovaLoja(BaseModel):
    nome: str

@app.post("/lojas")
def criar_loja(loja: NovaLoja):
    # Manda o nome da loja lá para o banco de dados Supabase
    resposta = supabase.table("lojas").insert({"nome": loja.nome}).execute()
    return {"mensagem": "Loja criada com sucesso!", "dados": resposta.data}