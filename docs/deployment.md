# Deployment Guide

## Production Checklist

### Security

- [ ] Generate strong secrets: `openssl rand -hex 32`
- [ ] Set `APP_SECRET_KEY` and `JWT_SECRET_KEY` in production `.env`
- [ ] Set `APP_ENV=production` and `APP_DEBUG=false`
- [ ] Configure HTTPS/TLS at the load balancer or Nginx
- [ ] Restrict CORS origins to your domain
- [ ] Rotate OpenAI API keys regularly

### Database

```bash
# Run migrations before starting the app
docker compose exec backend alembic upgrade head
```

### Environment Variables

Copy `.env.example` and configure all required variables. Critical production settings:

```env
APP_ENV=production
APP_DEBUG=false
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
OPENAI_API_KEY=sk-...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=...
OTEL_ENABLED=true
```

### Docker Compose (Production)

```bash
docker compose -f docker-compose.yml up -d --build
```

### Health Monitoring

Configure your orchestrator (Kubernetes, ECS) with:

- **Liveness:** `GET /api/v1/health/live`
- **Readiness:** `GET /api/v1/health/ready`
- **Metrics:** `GET /api/v1/metrics` (Prometheus scrape)

### Scaling

- **Backend:** Scale horizontally behind Nginx load balancer
- **PostgreSQL:** Use managed service (RDS, Cloud SQL)
- **Redis:** Use managed Redis (ElastiCache, Memorystore)
- **Qdrant:** Use Qdrant Cloud or clustered deployment
- **Celery workers:** Scale independently for document processing

### Observability

- Enable LangSmith tracing for LLM debugging
- Enable OpenTelemetry for distributed tracing
- Scrape Prometheus metrics from `/api/v1/metrics`
- Configure structured log aggregation (JSON logs via structlog)
