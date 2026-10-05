# Backup and disaster recovery

Run `ops/backup.sh` from a host with `pg_dump`, `curl`, and the AWS CLI installed. The script creates a timestamped backup containing:

- PostgreSQL in custom dump format;
- a Qdrant collection snapshot request result;
- the local upload volume, when used;
- an S3-to-S3 copy when `STORAGE_BACKEND=s3`.

Required variables are `PGPASSWORD` and, for S3 mode, `S3_BUCKET`. Optional variables include `BACKUP_ROOT`, `BACKUP_RETENTION_DAYS`, `QDRANT_URL`, `QDRANT_COLLECTION`, and `S3_BACKUP_BUCKET`.

Restore PostgreSQL with `pg_restore --clean --if-exists --dbname "$DATABASE_URL" postgres.dump`. Restore local uploads by extracting `uploads.tar.gz` into the configured upload volume. Qdrant snapshots must be downloaded into the Qdrant snapshot directory or restored through the Qdrant snapshot API according to the deployed Qdrant version. S3 restores should copy the timestamped backup prefix back to the active bucket.

Backups must be copied to a separate account or region and tested regularly. A production deployment should schedule this script at least daily, retain multiple recovery points, and perform a quarterly restore exercise.
# Deployment Guide

## Production Checklist

### Security

- [ ] Generate strong secrets: `openssl rand -hex 32`
- [ ] Set `APP_SECRET_KEY` and `JWT_SECRET_KEY` in production `.env`
- [ ] Set `APP_ENV=production` and `APP_DEBUG=false`
- [ ] Configure HTTPS/TLS at the load balancer or Nginx
- [ ] Restrict CORS origins to your domain
- [ ] Rotate OpenAI API keys regularly
- [ ] Configure OIDC or SAML signing and callback settings when enterprise SSO is enabled
- [ ] Use a dedicated, rotated `SCIM_BEARER_TOKEN` and set `SCIM_ORGANIZATION_ID`
- [ ] Verify tenant-scoped ACLs and group membership before enabling external synchronization

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

For SAML deployments also set `SAML_ENABLED`, `SAML_IDP_ENTITY_ID`, `SAML_IDP_SSO_URL`,
`SAML_IDP_X509_CERT`, `SAML_SP_ENTITY_ID`, and `SAML_ACS_URL`. Register the ACS URL with
the identity provider and ensure the reverse proxy preserves the external HTTPS host.

SCIM provisioning is exposed below `/api/v1/scim/v2.0`. The bearer token is independent
from user JWTs. Users are scoped to `SCIM_ORGANIZATION_ID`; delete operations deactivate
users, while group updates are applied to document ACL resolution within the tenant.

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

### Very large repositories

For very large, multi-terabyte collections:

- use S3 or MinIO as the source of truth, not the local upload volume;
- keep API instances stateless and scale ingestion and connector workers independently;
- provision Qdrant based on chunk count, vector dimensions, replication, and index memory;
- use managed PostgreSQL and Redis with backups, replication, and monitoring;
- tune embedding batches and worker concurrency against provider rate limits;
- run a representative load test covering initial indexing, incremental sync, ACL filtering,
  backup, restore, and concurrent queries.

The application supports streaming uploads, asynchronous Redis Streams ingestion, retries,
dead-letter replay, batched embeddings, incremental Drive/SharePoint sync, and tenant-scoped
ACL filtering. These capabilities enable the architecture to handle very large collections,
but capacity and latency depend on the selected storage, vector, database, and embedding
infrastructure and must be measured before go-live.

### Observability

- Enable LangSmith tracing for LLM debugging
- Enable OpenTelemetry for distributed tracing
- Scrape Prometheus metrics from `/api/v1/metrics`
- Configure structured log aggregation (JSON logs via structlog)

### Frontend security verification

From `frontend/`, run:

```bash
npm audit --omit=dev
npm run type-check
npm run build
```

The production dependency audit should report zero vulnerabilities before deployment.
