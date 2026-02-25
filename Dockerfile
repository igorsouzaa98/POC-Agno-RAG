FROM python:3.13-slim

# libgomp1 é necessária para FastEmbed (ONNX Runtime)
RUN apt-get update && apt-get install -y libgomp1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia dependências primeiro para aproveitar cache de camadas
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e . 2>/dev/null; true

# Copia o restante do projeto
COPY . .
RUN pip install --no-cache-dir -e .

# Pré-indexa a knowledge base dentro da imagem
# (LanceDB + modelo FastEmbed ficam baked no container — sem cold start de download)
RUN python scripts/build_knowledge.py --recreate

EXPOSE 8080

# Railway injeta $PORT automaticamente; fallback 8080 para Docker local
CMD ["sh", "-c", "uvicorn src.agent_os_server:app --host 0.0.0.0 --port ${PORT:-8080}"]
