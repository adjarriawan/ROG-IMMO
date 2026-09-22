# Backend Setup

## Ollama (host machine, not Dockerized)

1. Install Ollama: https://ollama.com
2. Start server: `ollama serve`
3. Pull models:
   - `ollama pull llama3`
   - `ollama pull nomic-embed-text`
4. Verify: `curl http://localhost:11434/api/tags`

## Database

See `docker-compose.yml` at repo root. Run `docker compose up -d postgres`, then
`alembic upgrade head` from `backend/` to apply migrations.
