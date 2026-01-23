# Docker Setup Guide

This guide explains how to run the WakaAgent backend using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+

## Quick Start

1. **Build and start all services:**

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database (port 5432)
- Redis (port 6379)
- FastAPI backend (port 8000)
- Celery worker

2. **View logs:**

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
```

3. **Stop services:**

```bash
docker-compose down
```

4. **Stop and remove volumes (clean slate):**

```bash
docker-compose down -v
```

## Services

### Backend API
- **Container:** `wakaagent-backend`
- **Port:** 8000
- **Health Check:** `http://localhost:8000/api/v1/healthz`
- **API Docs:** `http://localhost:8000/api/v1/docs`

### PostgreSQL
- **Container:** `wakaagent-postgres`
- **Port:** 5432
- **Database:** `wakaagent`
- **User:** `postgres`
- **Password:** `postgres` (change in production!)

### Redis
- **Container:** `wakaagent-redis`
- **Port:** 6379
- Used for realtime features and Celery task queue

### Celery Worker
- **Container:** `wakaagent-celery-worker`
- Processes background tasks

## Environment Variables

Create a `.env` file in the `backend/` directory to override default values:

```env
# Security (REQUIRED in production)
JWT_SECRET=your-secret-key-here

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# AI Services (optional)
GROQ_API_KEY=your-groq-api-key
OLLAMA_HOST=http://host.docker.internal:11434
WHISPER_HOST=http://host.docker.internal:8000

# Render/MCP (optional)
RENDER_API_KEY=your-render-api-key
```

The `.env` file is automatically loaded by docker-compose.

## Database Migrations

Migrations run automatically on backend startup via the `docker-entrypoint.sh` script. The script waits for PostgreSQL to be ready before running `alembic upgrade head`.

To run migrations manually:

```bash
docker-compose exec backend alembic upgrade head
```

To create a new migration:

```bash
docker-compose exec backend alembic revision --autogenerate -m "description"
```

## Development

### Rebuild after code changes:

```bash
docker-compose build backend
docker-compose up -d backend
```

### Run commands inside containers:

```bash
# Python shell
docker-compose exec backend python

# Run tests
docker-compose exec backend pytest

# Access database
docker-compose exec postgres psql -U postgres -d wakaagent
```

### View persistent data:

```bash
# ChromaDB data
docker volume inspect wakaagent-backend_chromadb_data

# Exports
docker volume inspect wakaagent-backend_exports_data

# Database
docker volume inspect wakaagent-backend_pgdata
```

## Production Considerations

1. **Change default passwords:**
   - Update `POSTGRES_PASSWORD` in `docker-compose.yaml`
   - Update `JWT_SECRET` in `.env` file
   - Use strong, randomly generated secrets

2. **Security:**
   - Don't expose database/Redis ports publicly
   - Use environment-specific `.env` files
   - Enable SSL/TLS for database connections
   - Restrict CORS origins

3. **Scaling:**
   - Use external managed databases (RDS, Cloud SQL, etc.)
   - Use managed Redis (ElastiCache, Cloud Memorystore, etc.)
   - Scale Celery workers: `docker-compose up -d --scale celery-worker=3`

4. **Monitoring:**
   - Add logging aggregation (ELK, Loki, etc.)
   - Set up health check monitoring
   - Monitor resource usage

5. **Backups:**
   - Regular database backups
   - Backup ChromaDB volumes
   - Backup export files

## Troubleshooting

### Backend won't start:
```bash
# Check logs
docker-compose logs backend

# Verify database is ready
docker-compose exec postgres pg_isready -U postgres
```

### Migration errors:
```bash
# Check database connection
docker-compose exec backend python -c "from app.core.config import get_settings; print(get_settings().DATABASE_URL)"

# Run migrations manually
docker-compose exec backend alembic upgrade head
```

### Port conflicts:
If ports 5432, 6379, or 8000 are already in use, modify the port mappings in `docker-compose.yaml`:

```yaml
ports:
  - "8001:8000"  # Use 8001 instead of 8000
```

### Clear everything and start fresh:
```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

## Building the Image

To build the Docker image manually:

```bash
docker build -t wakaagent-backend:latest .
```

To build without cache:

```bash
docker build --no-cache -t wakaagent-backend:latest .
```
