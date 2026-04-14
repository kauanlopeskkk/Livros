from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from sqlalchemy import create_engine, Column, Integer, String , Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import redis.asyncio as redis
import json
import os
import logging

logging.basicConfig(level=logging.INFO)

DATABASE_URL = "sqlite:///./livros.db"

Engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=Engine)
Base = declarative_base()

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

senha_admin = os.getenv("SENHA_ADMIN", "admin")  
senha = os.getenv("SENHA", "1010")

app = FastAPI(title="Livros API Criando com sucesso")

security = HTTPBasic()


class Livro(Base):
    __tablename__ = "livros"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True)
    autor = Column(String, index=True)
    ano_publicacao = Column(Integer, index=True)
    preco = Column(Float, index=True)


Base.metadata.create_all(bind=Engine)


class LivroCreate(BaseModel):
    titulo: str
    autor: str
    ano_publicacao: int
    preco: float

async def salvar_livro_redis(Livro_id:int , Livro: LivroCreate):
    await redis_client.set(f"Livro:{Livro_id}", json.dumps(Livro.dict()))

async def deletar_livro_redis(Livro_id: int):
    await redis_client.delete(f"Livro:{Livro_id}")


def sessao_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def autenticar_usuario(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, senha_admin)
    correct_password = secrets.compare_digest(credentials.password, senha)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


@app.get("/")
def read_root():
    return {"message": "Bem-vindo à API de Livros!"}


@app.get("/debug/redis")
async def ver_livros_redis():
    chaves = redis_client.scan("Livro:*")
    livros = []

    for chave in chaves:
        valor = await redis_client.get(chave)
        ttl = await redis_client.ttl(chave)
        livros.append({
            "chave": chave,
            "valor": json.loads(valor),
            "ttl": ttl
        })
    return {"livros_redis": livros}



@app.post("/Livros/")
async def Criar_livro(
    livro: LivroCreate,
    db: Session = Depends(sessao_db),
    credentials: HTTPBasicCredentials = Depends(autenticar_usuario)
):
    db_livro = db.query(Livro).filter(
        (Livro.titulo == livro.titulo) &
        (Livro.autor == livro.autor) &
        (Livro.ano_publicacao == livro.ano_publicacao) &
        (Livro.preco == livro.preco)
    ).first()

    if db_livro:
        raise HTTPException(status_code=400, detail="Livro já existe NA ID")

    novo_livro = Livro(
        titulo=livro.titulo,
        autor=livro.autor,
        ano_publicacao=livro.ano_publicacao,
        preco=livro.preco
    )



    db.add(novo_livro)
    db.commit()
    db.refresh(novo_livro)

    await salvar_livro_redis(novo_livro.id, livro)

    return {
        "id": novo_livro.id,
        "titulo": novo_livro.titulo,
        "autor": novo_livro.autor,
        "ano_publicacao": novo_livro.ano_publicacao,
        "preco": novo_livro.preco
    }


@app.get("/Livros/")
async def listar_livros(
    page: int = 1,
    size: int = 10,
    db: Session = Depends(sessao_db),
    credentials: HTTPBasicCredentials = Depends(autenticar_usuario)
):
    if page < 1 or size <1:
        raise HTTPException(status_code=400, detail="Page e size devem ser maiores que 0")
    cache_key = f"Livros:page={page}:size={size}"
    cached = redis_client.get(cache_key)    
    if cached:
        return json.loads(cached)
    livros = db.query(Livro).offset((page - 1) * size).limit(size).all()    

    if not livros:
        raise HTTPException(status_code=404, detail="Nenhum livro encontrado")
    
    total_livros = db.query(Livro).count()
    
    reposta = {
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

    redis_client.setex(cache_key, 600, json.dumps(reposta))

    return reposta

@app.put("/Livros/{livro_id}")
async def atualizar_livro(
    livro_id: int,
    livro: LivroCreate,
    db: Session = Depends(sessao_db),
    credentials: HTTPBasicCredentials = Depends(autenticar_usuario)
):
    db_livro = db.query(Livro).filter(Livro.id == livro_id).first()

    if not db_livro:
        raise HTTPException(status_code=404, detail="Livro não encontrado")

    db_livro.titulo = livro.titulo
    db_livro.autor = livro.autor
    db_livro.ano_publicacao = livro.ano_publicacao
    db_livro.preco = livro.preco

    db.commit()
    db.refresh(db_livro)


    for key in redis_client.scan_iter("Livros:*"):
        redis_client.delete(key)

    await salvar_livro_redis(livro_id, livro)

    return {
        "id": db_livro.id,
        "titulo": db_livro.titulo,
        "autor": db_livro.autor,
        "ano_publicacao": db_livro.ano_publicacao,
        "preco": db_livro.preco
    }


@app.delete("/Livros/{livro_id}")
async def deletar_livro(
    livro_id: int,
    db: Session = Depends(sessao_db),
    credentials: HTTPBasicCredentials = Depends(autenticar_usuario)
):
    db_livro = db.query(Livro).filter(Livro.id == livro_id).first()

    if not db_livro:
        raise HTTPException(status_code=404, detail="Livro não encontrado")

    db.delete(db_livro)
    db.commit()

    # Invalidar cache
    for key in redis_client.keys("Livros:*"):
        redis_client.delete(key)

    await deletar_livro_redis(livro_id)

    return {"message": "Livro deletado com sucesso"}