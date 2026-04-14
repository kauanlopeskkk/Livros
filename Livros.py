from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import asyncio


DATABASE_URL = "sqlite:///./livros.db"

Engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=Engine)
Base = declarative_base()

Senha_admin = "admin123"  
Senha_Senha = "1010"

app = FastAPI(title="Livros API Criando com sucesso")

security = HTTPBasic()

# corrigido lista
meu_livros = [
    "O Senhor dos Anéis",
    "Harry Potter e a Pedra Filosofal",
    "O Código Da Vinci",
    "A Guerra dos Tronos",
    "O Hobbit"
]


class Livro(Base):
    __tablename__ = "livros"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True)
    autor = Column(String, index=True)
    ano_publicacao = Column(Integer, index=True)
    preco = Column(Integer, index=True)


Base.metadata.create_all(bind=Engine)


class LivroCreate(BaseModel):
    titulo: str
    autor: str
    ano_publicacao: int
    preco: int


def sessao_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def autenticar_usuario(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, Senha_admin)
    correct_password = secrets.compare_digest(credentials.password, Senha_Senha)

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



async def listar_livros1():
    await asyncio.sleep(0.1)
    return {"livros": meu_livros}


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

    await asyncio.sleep(0.1)

    db.add(novo_livro)
    db.commit()
    db.refresh(novo_livro)

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
    livros = db.query(Livro).offset((page - 1) * size).limit(size).all()

    if not livros:
        raise HTTPException(status_code=404, detail="Nenhum livro encontrado")
    await asyncio.sleep(0.1)
    
    pydantic_livros = [LivroCreate(
        titulo=livro.titulo,
        autor=livro.autor,
        ano_publicacao=livro.ano_publicacao,
        preco=livro.preco
    ) for livro in livros]
  
    return {"livros": pydantic_livros}


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

    await asyncio.sleep(0.1)

    return {"message": "Livro deletado com sucesso"}