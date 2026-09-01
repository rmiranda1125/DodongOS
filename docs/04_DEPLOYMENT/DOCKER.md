# Docker

Production image is built from `/Dockerfile` (context = repo root):
`docker build -t dodong-os:latest .`

Runs Django under gunicorn as a non-root user; static collected at build time;
migrations are a separate release step. See **`PRODUCTION.md`**.
