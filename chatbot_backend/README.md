# Django Chatbot Backend

Production-ready Django backend for a chatbot with Groq LLM integration and PostgreSQL-based conversation history management.

## Features

- 🤖 **AI Chat**: Groq LLM integration with conversation history
- 💾 **PostgreSQL**: Persistent conversation storage
- 🔄 **REST API**: DRF-based API with Swagger documentation
- 🐳 **Docker Ready**: Production-ready Docker configuration
- 📊 **Feedback System**: User feedback on AI responses

## Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your Groq API key and database credentials
```

### 2. Configure Database

```bash
# Create PostgreSQL database
createdb chatbot_db

# Or using Docker
docker run -d --name chatbot_db \
  -e POSTGRES_DB=chatbot_db \
  -e POSTGRES_PASSWORD=yourpassword \
  -p 5432:5432 \
  postgres:16
```

### 3. Run Migrations

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Start Development Server

```bash
python manage.py runserver
```

### 5. Access API

- **API Docs**: http://localhost:8000/api/docs/
- **Admin**: http://localhost:8000/admin/

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/chat/message/` | POST | Send message & get AI response |
| `/api/v1/conversations/` | GET | List all conversations |
| `/api/v1/conversations/{id}/` | GET | Get conversation details |
| `/api/v1/conversations/{id}/messages/` | GET | Get conversation messages |
| `/api/v1/conversations/{id}/archive/` | POST | Archive conversation |
| `/api/v1/feedback/` | POST | Submit message feedback |

## Example Usage

### Send a Message

```bash
curl -X POST http://localhost:8000/api/v1/chat/message/ \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, how are you?"}'
```

### Continue Conversation

```bash
curl -X POST http://localhost:8000/api/v1/chat/message/ \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Tell me more", "conversation_id": "<uuid>"}'
```

## Production Deployment

### Using Docker Compose

```bash
# Set environment variables
export DB_PASSWORD=your_secure_password
export DJANGO_SECRET_KEY=your_secret_key
export LLM_API_KEY=your_groq_api_key

# Build and run
docker-compose up -d
```

## Project Structure

```
chatbot_backend/
├── apps/
│   ├── chat/          # Chat functionality
│   ├── core/          # Shared utilities
│   └── users/         # Auth (Phase 2)
├── config/
│   ├── settings/      # Django settings
│   ├── urls.py
│   └── wsgi.py
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_API_KEY` | Groq API key | Required |
| `LLM_MODEL` | Groq model name | `llama-3.3-70b-versatile` |
| `DB_NAME` | Database name | `chatbot_db` |
| `MAX_HISTORY_MESSAGES` | Messages in context | `20` |

## License

MIT
