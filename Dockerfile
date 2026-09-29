# Imagen única para los servicios (spec: openspec/changes/produccion).
# Zero trust: bases fijadas por digest, dependencias exactas del lock (hashes), usuario sin privilegios.
FROM ghcr.io/astral-sh/uv:0.9.26@sha256:9a23023be68b2ed09750ae636228e903a54a05ea56ed03a934d00fe9fbeded4b AS uv

FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --extra prod --no-install-project
COPY labs/ labs/
COPY jev/ jev/
COPY servicios/ servicios/
COPY data/calibracion-bitext-demo.json data/
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER 10001
ENV PATH="/app/.venv/bin:$PATH"
