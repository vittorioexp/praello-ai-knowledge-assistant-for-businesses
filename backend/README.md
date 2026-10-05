# Praello AI - Backend

Python 3.13 / FastAPI backend for Praello AI Knowledge Assistant for Businesses.

See the [root README](../README.md) for full documentation.

The ingestion worker is started with `python -m enterprise_ai.worker`. It consumes durable Redis Stream jobs and sends permanently failing jobs to `enterprise_ai:ingestion:dead-letter` after `MAX_INGESTION_ATTEMPTS` attempts. Set `STORAGE_BACKEND=s3` to use the S3-compatible object storage adapter for uploads and remote connector documents.
