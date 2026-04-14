# 📚 Livros API com FastAPI + Redis

Este projeto consiste em uma API REST para gerenciamento de livros, desenvolvida com **FastAPI**, utilizando **SQLite** como banco de dados e **Redis** como sistema de cache para melhorar a performance.

---

## 🚀 Tecnologias utilizadas

* Python 3.10+
* FastAPI
* SQLAlchemy
* SQLite
* Redis
* Uvicorn

---

## 📦 Funcionalidades

* ✅ Criar livros
* ✅ Listar livros com paginação
* ✅ Atualizar livros
* ✅ Deletar livros
* ✅ Autenticação básica (HTTP Basic)
* ✅ Cache com Redis para otimizar consultas
* ✅ Invalidação de cache automática ao modificar dados

---

## ⚙️ Pré-requisitos

Antes de começar, você precisa ter instalado:

* Python 3.10+
* Redis
* Pip

---

## 🔧 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/livros-api.git
cd livros-api
```

---

### 2. Crie um ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

---

### 3. Instale as dependências

```bash
pip install fastapi uvicorn sqlalchemy redis
```

---

## 🧠 Configuração do Redis

### ▶️ Rodando localmente

Certifique-se de que o Redis está rodando:

```bash
redis-server
```

---

### 🐳 Usando Docker (recomendado)

```bash
docker run -d -p 6379:6379 redis
```

---

## ▶️ Executando a aplicação

```bash
uvicorn main:app --reload
```

A API estará disponível em:

👉 http://127.0.0.1:8000

Documentação interativa:

👉 http://127.0.0.1:8000/docs

---

## 🔐 Autenticação

A API utiliza autenticação básica (HTTP Basic):

* **Usuário:** admin123
* **Senha:** 1010

---

## 📌 Endpoints

### 🔹 Criar livro

```http
POST /Livros/
```

Exemplo:

```json
{
  "titulo": "Clean Code",
  "autor": "Robert C. Martin",
  "ano_publicacao": 2008,
  "preco": 50
}
```

---

### 🔹 Listar livros (com cache)

```http
GET /Livros/?page=1&size=10
```

📌 Estratégia:

* Primeiro busca no Redis
* Se não encontrar, consulta o banco
* Salva no Redis com TTL de 600 segundos

---

### 🔹 Atualizar livro

```http
PUT /Livros/{id}
```

📌 Ação:

* Atualiza no banco
* Remove cache relacionado

---

### 🔹 Deletar livro

```http
DELETE /Livros/{id}
```

📌 Ação:

* Remove do banco
* Remove do Redis

---

### 🔹 Debug Redis

```http
GET /debug/redis
```

Mostra todas as chaves armazenadas no Redis.

---

## ⚡ Cache com Redis

### 📌 Estratégia utilizada:

* Cache de listagem paginada:

  ```
  Livros:page={page}:size={size}
  ```

* Cache individual:

  ```
  Livro:{id}
  ```

### ⏱ TTL (tempo de expiração):

* 600 segundos (10 minutos)

### 🔄 Invalidação:

* O cache é limpo sempre que um livro é:

  * atualizado
  * deletado

---

## 🧪 Testando a API

### ✔ Usando curl

#### Criar livro

```bash
curl -X POST "http://127.0.0.1:8000/Livros/" \
-u admin123:1010 \
-H "Content-Type: application/json" \
-d '{"titulo":"Teste","autor":"Autor","ano_publicacao":2024,"preco":100}'
```

---

#### Listar livros

```bash
curl -X GET "http://127.0.0.1:8000/Livros/?page=1&size=5" \
-u admin123:1010
```

---

#### Atualizar livro

```bash
curl -X PUT "http://127.0.0.1:8000/Livros/1" \
-u admin123:1010 \
-H "Content-Type: application/json" \
-d '{"titulo":"Novo","autor":"Autor","ano_publicacao":2024,"preco":120}'
```

---

#### Deletar livro

```bash
curl -X DELETE "http://127.0.0.1:8000/Livros/1" \
-u admin123:1010
```

---

## 📊 Benefícios do uso do Redis

* 🚀 Redução no tempo de resposta
* 📉 Menor carga no banco de dados
* ⚡ Melhor performance em requisições repetidas

---

## 📌 Melhorias futuras

* 🔐 Usar variáveis de ambiente para credenciais
* ⚡ Utilizar Redis assíncrono (`redis.asyncio`)
* 📖 Adicionar endpoint GET por ID
* 🐳 Dockerizar toda a aplicação
* 📊 Adicionar logs e monitoramento

---

## 👨‍💻 Autor

Projeto desenvolvido para fins de estudo com foco em:

* FastAPI
* Cache com Redis
* Boas práticas de API REST

---
