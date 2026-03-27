import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from supabase import create_client, Client
from pydantic import BaseModel, Field, validator
import mercadopago

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CONFIGURAÇÃO — use variáveis de ambiente em produção, chaves como fallback
# ---------------------------------------------------------------------------
URL_SUPABASE  = os.getenv("SUPABASE_URL",  "https://sdffwrpacvtjncuqtrft.supabase.co")
CHAVE_SUPABASE = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNkZmZ3cnBhY3Z0am5jdXF0cmZ0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ1NjU3NTAsImV4cCI6MjA5MDE0MTc1MH0.FarfM9aF-rKZOqEfhzt6Oqar1aN3H75wkHoySMAICcg")
TOKEN_MP      = os.getenv("MERCADOPAGO_TOKEN", "TEST-7623525379052412-032620-4605c07246d1051aab714eb92804a977-331454528")

# ---------------------------------------------------------------------------
# CLIENTES — inicializados uma vez
# ---------------------------------------------------------------------------
banco: Client = create_client(URL_SUPABASE, CHAVE_SUPABASE)
sdk           = mercadopago.SDK(TOKEN_MP)


# ---------------------------------------------------------------------------
# LIFESPAN — startup / shutdown logs
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 Motor SaaS iniciado — Supabase e MercadoPago prontos.")
    yield
    log.info("🛑 Motor SaaS encerrado.")


# ---------------------------------------------------------------------------
# APP
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Motor SaaS",
    version="1.1.0",
    description="Backend da Vitrine — produtos, lojas e pagamentos.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# HANDLER GLOBAL DE ERROS INESPERADOS
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    log.error(f"Erro não tratado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "mensagem": "Erro interno. Tente novamente."},
    )


# ---------------------------------------------------------------------------
# SCHEMAS
# ---------------------------------------------------------------------------
class NovoProduto(BaseModel):
    nome:     str   = Field(..., min_length=1, max_length=200)
    preco:    float = Field(..., gt=0)
    foto_url: str   = Field(..., min_length=1)
    loja_id:  str   = Field(..., min_length=1)
    user_id:  str   = Field(..., min_length=1)

    @validator("preco")
    def preco_valido(cls, v):
        return round(v, 2)  # garante no máximo 2 casas decimais


class NovoPedido(BaseModel):
    titulo_produto: str   = Field(..., min_length=1, max_length=200)
    preco:          float = Field(..., gt=0)

    @validator("preco")
    def preco_valido(cls, v):
        return round(v, 2)


# ---------------------------------------------------------------------------
# UTILS
# ---------------------------------------------------------------------------
def _user_id_valido(user_id: str | None) -> str | None:
    """Retorna user_id limpo ou None se for um valor inválido vindo do frontend."""
    if not user_id or user_id.strip() in ("", "undefined", "null"):
        return None
    return user_id.strip()


# ---------------------------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Sistema"])
def health():
    """Endpoint para monitoramento — retorna 200 se o motor está no ar."""
    return {"status": "ok", "versao": "1.1.0"}


# ---------------------------------------------------------------------------
# LOJAS
# ---------------------------------------------------------------------------
@app.get("/lojas", tags=["Lojas"])
def pegar_lojas():
    try:
        resposta = banco.table("lojas").select("*").order("nome").execute()
        log.info(f"Lojas retornadas: {len(resposta.data)}")
        return resposta.data
    except Exception as e:
        log.error(f"Erro ao buscar lojas: {e}")
        raise HTTPException(status_code=500, detail="Não foi possível carregar as lojas.")


# ---------------------------------------------------------------------------
# PRODUTOS
# ---------------------------------------------------------------------------
@app.get("/produtos", tags=["Produtos"])
def pegar_produtos(user_id: str = Query(default=None)):
    uid = _user_id_valido(user_id)
    try:
        query = banco.table("produtos").select("*").order("created_at", desc=True)
        if uid:
            query = query.eq("user_id", uid)
        resposta = query.execute()
        log.info(f"Produtos retornados: {len(resposta.data)} | user_id={uid or 'todos'}")
        return resposta.data
    except Exception as e:
        log.error(f"Erro ao buscar produtos: {e}")
        raise HTTPException(status_code=500, detail="Não foi possível carregar os produtos.")


@app.post("/produtos", status_code=201, tags=["Produtos"])
def criar_produto(item: NovoProduto):
    try:
        resposta = banco.table("produtos").insert({
            "nome":     item.nome,
            "preco":    item.preco,
            "foto_url": item.foto_url,
            "loja_id":  item.loja_id,
            "user_id":  item.user_id,
        }).execute()

        if not resposta.data:
            raise HTTPException(status_code=500, detail="Produto não foi salvo.")

        log.info(f"Produto criado: '{item.nome}' | loja={item.loja_id} | user={item.user_id}")
        return {"status": "ok", "dados": resposta.data}

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Erro ao criar produto: {e}")
        raise HTTPException(status_code=500, detail="Não foi possível salvar o produto.")


# ---------------------------------------------------------------------------
# PAGAMENTO
# ---------------------------------------------------------------------------
@app.post("/checkout", tags=["Pagamento"])
def criar_pagamento(pedido: NovoPedido):
    try:
        dados_pagamento = {
            "items": [{
                "title":      pedido.titulo_produto,
                "quantity":   1,
                "unit_price": pedido.preco,
                "currency_id": "BRL",
            }],
            "marketplace_fee": 5.00,
            "payment_methods": {
                "excluded_payment_types": [],
                "installments": 12,
            },
        }

        resposta_mp = sdk.preference().create(dados_pagamento)
        response    = resposta_mp.get("response", {})

        if "error" in response:
            log.error(f"MercadoPago recusou a preferência: {response}")
            raise HTTPException(status_code=502, detail="Erro ao criar preferência de pagamento.")

        link = response.get("init_point") or response.get("sandbox_init_point")
        log.info(f"Checkout criado: '{pedido.titulo_produto}' R${pedido.preco:.2f}")

        return {"link_de_pagamento": link}  # ← mesmo campo que o frontend já espera

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Erro no checkout: {e}")
        raise HTTPException(status_code=500, detail="Não foi possível gerar o link de pagamento.")