# Image de l'API, en plusieurs étapes :
#   1. « deps » et « deps-dev » installent les bibliothèques Python dans un environnement isolé (/opt/venv) ;
#   2. « dev » = l'API + pytest + les tests (utilisée par docker compose et la CI) ;
#   3. « prod » (dernière étape, celle construite par défaut) = l'API seule, sans outils de test ni pip cache.
# Les étapes finales ne gardent que /opt/venv et le code : l'image reste petite, et tourne sans droits root.

FROM python:3.12-slim AS deps
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM deps AS deps-dev
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

# Base commune des images finales : utilisateur sans droits, pas de fichiers .pyc, journaux immédiats.
FROM python:3.12-slim AS base
ENV PATH=/opt/venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 10001 tri
WORKDIR /app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS dev
COPY --from=deps-dev /opt/venv /opt/venv
COPY app ./app
COPY config ./config
COPY tests ./tests
COPY pytest.ini .
USER tri

FROM base AS prod
COPY --from=deps /opt/venv /opt/venv
COPY app ./app
COPY config ./config
USER tri
