FROM python:3.12-slim

WORKDIR /app

# Dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code (sans .env — les vars sont injectées par Railway)
COPY . .

# Port non nécessaire pour un bot polling, mais Railway l'exige
ENV PORT=8080

CMD ["python", "main.py"]
