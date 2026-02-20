import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Model ID - configurado via .env para facilitar troca
# Opções disponíveis:
#   claude-haiku-4-5-20251001   (rápido, econômico)
#   claude-sonnet-4-5-20251001  (balanceado)
#   claude-opus-4-5-20251001    (mais capaz)
MODEL_ID = os.getenv("MODEL_ID", "claude-haiku-4-5-20251001")

KNOWLEDGE_BASE_DIR = "knowledge"
VECTOR_DB_PATH = "data/lancedb"
