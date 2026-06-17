# Intelligent Agent — RAG Legal Chatbot Backend

A production-ready **Django** backend for an AI chatbot with
Retrieval-Augmented Generation (RAG) over a legal-document knowledge base. It
combines a **Groq-hosted LLM** with **Pinecone** vector search and
**PostgreSQL**-backed conversation history, exposed through a documented REST API.

## What this project does

- **AI chat with memory** — answers user questions via a Groq LLM, keeping
  per-conversation history in PostgreSQL.
- **RAG over legal documents** — retrieves relevant chunks from a Pinecone vector
  store (built with LangChain) and grounds answers in them, citing source
  documents.
- **Document ingestion** — a management command processes and embeds documents
  into the vector store.
- **REST API** — Django REST Framework endpoints with Swagger/OpenAPI docs for
  sending messages, listing/archiving conversations, and submitting feedback.
- **User accounts & feedback** — user app plus a feedback system on AI responses.
- **Deployment-ready** — Docker, docker-compose, and Nginx configuration included.

## Tech stack

- **Django** + **Django REST Framework**
- **LangChain** + **Groq** (`langchain-groq`) — LLM orchestration
- **Pinecone** — vector database for RAG
- **PostgreSQL** — conversation and app data
- **Redis** — caching / async support
- **Docker** + **Nginx** — containerized deployment

## Repository layout

The Django project lives in [`chatbot_backend/`](chatbot_backend/):

```
chatbot_backend/
├── apps/
│   ├── chat/      # Chat endpoints, models, chat service
│   ├── rag/       # RAG: document processor, vector store, LangChain agent
│   ├── users/     # Authentication & user management
│   └── core/      # Shared utilities, middleware, pagination
├── config/        # Settings (base/development/production), URLs, WSGI/ASGI
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
└── requirements.txt
```

## Quick start

> The full setup guide — API endpoints, example requests, configuration table,
> and Docker deployment — is in [`chatbot_backend/README.md`](chatbot_backend/README.md).

```bash
cd chatbot_backend

# 1. Create a virtualenv and install dependencies
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment (never commit real keys)
cp .env.example .env
# Edit .env: set LLM_API_KEY (Groq), PINECONE_API_KEY, DB credentials, etc.

# 3. Migrate and run
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- API docs: http://localhost:8000/api/docs/
- Admin: http://localhost:8000/admin/

### Ingest documents for RAG
```bash
python manage.py ingest_documents   # see apps/rag/management/commands/
```

## Configuration

Key environment variables (see `chatbot_backend/.env.example` for the full list):

| Variable           | Description                          |
|--------------------|--------------------------------------|
| `LLM_API_KEY`      | Groq API key                         |
| `LLM_MODEL`        | Groq model (e.g. `llama-3.3-70b-versatile`) |
| `PINECONE_API_KEY` | Pinecone API key                     |
| `PINECONE_INDEX_NAME` | Pinecone index (e.g. `legal-docs`) |
| `DB_*`             | PostgreSQL connection settings       |
| `DJANGO_SECRET_KEY`| Django secret key                    |

> ⚠️ Keep all secrets in `.env` (gitignored). Never commit real API keys.

## License

MIT
