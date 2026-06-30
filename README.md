# Poultry ERP AI Assistant

## Overview

This repository is a Poultry ERP application with a React/Vite frontend and a FastAPI backend. It supports user authentication, an AI-powered assistant, inventory tracking, document upload/processing, finance management, reports, voice input, translations, and session-based chat history.

---

## Project Structure

- `backend/`
  - `app/`: FastAPI application code
  - `Dockerfile`: backend container build file
  - `requirements.txt`: Python dependencies
  - `test_api.py`: smoke test script
- `frontend/`
  - `src/`: React application source files
  - `package.json`: frontend dependencies and scripts
  - `vite.config.ts`: Vite configuration
- `docker-compose.yml`: orchestrates backend, frontend, and database services

---

## Tech Stack

### Backend
- FastAPI
- SQLAlchemy (async)
- Pydantic / Pydantic Settings
- Uvicorn
- JWT auth with `python-jose`
- Password hashing with `passlib[bcrypt]`
- File upload support with `python-multipart`
- OCR helpers using `pypdf` and `Pillow`

### Frontend
- React + TypeScript
- Vite
- Axios
- React Router DOM
- Framer Motion
- Lucide Icons
- Recharts

### Database
- `docker-compose.yml` configures PostgreSQL (`postgres:16-alpine`) for Docker deployments.
- The backend supports SQLAlchemy async and is configured by default to use SQLite if no `DATABASE_URL` environment variable is provided.

  Default local fallback:
  - `sqlite+aiosqlite:///./poultry_erp.db`

  Docker Compose database URL:
  - `postgresql+asyncpg://postgres:postgres@db:5432/poultry_erp`

So yes: this project has a database.

---

## Authentication

Authentication is JWT-based.

### Available endpoints
- `POST /api/v1/auth/register` — create a new user and return a JWT access token
- `POST /api/v1/auth/login/json` — login existing users via email/password and return a JWT access token
- `GET /api/v1/auth/me` — retrieve current user profile with JWT
- `PUT /api/v1/auth/settings` — update preferences

### Frontend
- `frontend/src/contexts/AuthContext.tsx` stores the JWT token in `localStorage`
- `frontend/src/lib/api.ts` attaches `Authorization: Bearer <token>` to requests

### Dynamic login/signup

Yes — this app already supports dynamic login and registration:
- New users can sign up and receive a JWT
- Existing users can log in and receive a JWT
- All guarded backend routes use the JWT via `app/core/deps.py`

This means any user can register or sign in dynamically as long as they provide valid credentials.

---

## Document Upload Flow

The assistant document upload flow is staged and user-controlled:
- User selects a file locally first.
- No upload request is sent until the user clicks **Process Bill**.
- An optional prompt/context field can be entered before processing.
- If OCR confidence is low, the backend returns a confusion flag and the frontend asks for confirmation before final processing.
- Document type is inferred automatically from file text and filename, so the bill-type dropdown is no longer required.

---

## Assistant & Chat History

- Chat sessions are stored in the backend with `ChatSession` and `ChatMessage` models.
- The frontend shows sessions in a sidebar and supports deletion of conversations.
- A soft blue active style and hover animation are applied to the selected session.
- The delete button appears on hover and confirms deletion before removing the conversation.

---

## Runtime Configuration

Environment variables are loaded from `.env` if present.

Important variables:
- `DATABASE_URL`
- `SECRET_KEY`
- `ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `OPENAI_API_KEY`
- `OCR_SERVICE_URL`
- `CORS_ORIGINS`
- `UPLOAD_DIR`
- `MAX_UPLOAD_SIZE_MB`

---

## How to Run

### With Docker Compose

```bash
docker compose up --build
```

This starts:
- PostgreSQL database
- Backend on port `8000`
- Frontend on port `5173`

### Local development without Docker

1. Backend
   - Create and activate a Python environment
   - Install `backend/requirements.txt`
   - Set `DATABASE_URL` if using Postgres, otherwise SQLite fallback is used
   - Run backend with `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

2. Frontend
   - Install dependencies in `frontend/`
   - Run `npm run dev`

---

## What is used

- FastAPI backend
- React + Vite frontend
- Async SQLAlchemy for data modeling
- JWT auth for protected endpoints
- Document upload and OCR parsing
- User settings with multi-language support
- Voice assistant integration
- Session-based assistant history

## What is not used or still evolving

- Some assistant NLP branches and document classification may remain heuristic
- The file upload confirmation logic is user-driven and will ask for clarification only on low-confidence OCR results
- Translation labels are loaded from the backend, but the language dictionary may need expansion for full UI coverage

---

## Notes

- The project is designed for multi-user support via JWT.
- A database backend is present and can be either SQLite locally or PostgreSQL in Docker.
- The JWT auth model already supports new user signup and existing user login.
- The assistant can now infer bill type automatically and no longer depends on a manual bill category dropdown.
