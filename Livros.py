from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import redis
import json
import os
import logging

logging.basicConfig(level=logging.INFO)


# =========================
# DATABASE
# =========================

DATABASE_URL = "sqlite:///./livros.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


# =========================
# REDIS
# =========================

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)


# =========================
# CREDENCIAIS
# =========================

usuario_admin = os.getenv("USUARIO_ADMIN", "admin")
senha_admin = os.getenv("SENHA_ADMIN", "1010")


# =========================
# FASTAPI
# =========================

app = FastAPI(title="API de Livros")

security = HTTPBasic()


# =========================
# MODEL SQLALCHEMY
# =========================

class Livro(Base):
    __tablename__ = "livros"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True)
    autor = Column(String, index=True)
    ano_publicacao = Column(Integer, index=True)
    preco = Column(Float, index=True)


Base.metadata.create_all(bind=engine)


# =========================
# MODEL PYDANTIC
# =========================

class LivroCreate(BaseModel):
    titulo: str
    autor: str
    ano_publicacao: int
    preco: float


# =========================
# REDIS HELPERS
# =========================

def salvar_livro_redis(livro_id: int, livro: LivroCreate):
    redis_client.set(
        f"Livro:{livro_id}",
        json.dumps(livro.dict())
    )


def deletar_livro_redis(livro_id: int):
    redis_client.delete(
        f"Livro:{livro_id}"
    )


def limpar_cache():
    for key in redis_client.scan_iter("Livros:*"):
        redis_client.delete(key)


# =========================
# DB SESSION
# =========================

def sessao_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# AUTH
# =========================

def autenticar_usuario(
    credentials: HTTPBasicCredentials = Depends(security)
):
    usuario_correto = secrets.compare_digest(
        credentials.username,
        usuario_admin
    )

    senha_correta = secrets.compare_digest(
        credentials.password,
        senha_admin
    )

    if not (usuario_correto and senha_correta):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


# =========================
# ROOT
# =========================

@app.get("/")
def read_root():
    return {
        "message": "Bem-vindo à API de Livros!"
    }


# =========================
# DEBUG REDIS
# =========================

@app.get("/debug/redis")
def ver_livros_redis():
    livros = []

    for chave in redis_client.scan_iter("Livro:*"):
        valor = redis_client.get(chave)
        ttl = redis_client.ttl(chave)

        livros.append({
            "chave": chave,
            "valor": json.loads(valor),
            "ttl": ttl
        })

    return {
        "livros_redis": livros
    }


# =========================
# CREATE
# =========================

@app.post("/livros/")
def criar_livro(
    livro: LivroCreate,
    db: Session = Depends(sessao_db),
    _: HTTPBasicCredentials = Depends(autenticar_usuario)
):
    db_livro = db.query(Livro).filter(
        Livro.titulo == livro.titulo,
        Livro.autor == livro.autor
    ).first()

    if db_livro:
        raise HTTPException(
            status_code=400,
            detail="Livro já existe"
        )

    novo_livro = Livro(
        titulo=livro.titulo,
        autor=livro.autor,
        ano_publicacao=livro.ano_publicacao,
        preco=livro.preco
    )

    db.add(novo_livro)
    db.commit()
    db.refresh(novo_livro)

    salvar_livro_redis(
        novo_livro.id,
        livro
    )

    limpar_cache()

    return {
        "id": novo_livro.id,
        "titulo": novo_livro.titulo,
        "autor": novo_livro.autor,
        "ano_publicacao": novo_livro.ano_publicacao,
        "preco": novo_livro.preco
    }


# =========================
# READ
# =========================

@app.get("/livros/")
def listar_livros(
    page: int = 1,
    size: int = 10,
    db: Session = Depends(sessao_db),
    _: HTTPBasicCredentials = Depends(autenticar_usuario)
):
    if page < 1 or size < 1:
        raise HTTPException(
            status_code=400,
            detail="Page e size devem ser maiores que 0"
        )

    cache_key = f"Livros:page={page}:size={size}"

    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    livros = db.query(Livro)\
        .offset((page - 1) * size)\
        .limit(size)\
        .all()

    if not livros:
        raise HTTPException(
            status_code=404,
            detail="Nenhum livro encontrado"
        )

    total_livros = db.query(Livro).count()

    resposta = {
        "page": page,
        "size": size,
        "total": total_livros,
        "livros": [
            {
                "id": livro.id,
                "titulo": livro.titulo,
                "autor": livro.autor,
                "ano_publicacao": livro.ano_publicacao,
                "preco": livro.preco
            }
            for livro in livros
        ]
    }

    redis_client.setex(
        cache_key,
        600,
        json.dumps(resposta)
    )

    return resposta


# =========================
# UPDATE
# =========================

@app.put("/livros/{livro_id}")
def atualizar_livro(
    livro_id: int,
    livro: LivroCreate,
    db: Session = Depends(sessao_db),
    _: HTTPBasicCredentials = Depends(autenticar_usuario)
):
    db_livro = db.query(Livro).filter(
        Livro.id == livro_id
    ).first()

    if not db_livro:
        raise HTTPException(
            status_code=404,
            detail="Livro não encontrado"
        )

    db_livro.titulo = livro.titulo
    db_livro.autor = livro.autor
    db_livro.ano_publicacao = livro.ano_publicacao
    db_livro.preco = livro.preco

    db.commit()
    db.refresh(db_livro)

    limpar_cache()
    salvar_livro_redis(livro_id, livro)

    return {
        "message": "Livro atualizado com sucesso"
    }


# =========================
# DELETE
# =========================

@app.delete("/livros/{livro_id}")
def deletar_livro(
    livro_id: int,
    db: Session = Depends(sessao_db),
    _: HTTPBasicCredentials = Depends(autenticar_usuario)
):
    db_livro = db.query(Livro).filter(
        Livro.id == livro_id
    ).first()

    if not db_livro:
        raise HTTPException(
            status_code=404,
            detail="Livro não encontrado"
        )

    db.delete(db_livro)
    db.commit()

    limpar_cache()
    deletar_livro_redis(livro_id)

    return {
        "message": "Livro deletado com sucesso"
    }