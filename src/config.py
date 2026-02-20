import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Model ID - configurado via .env para facilitar troca
# Opções disponíveis:
#   gemini-2.5-flash-preview-04-17  (Google, econômico e rápido)
#   gemini-2.0-flash                (Google, muito rápido)
#   claude-haiku-4-5-20251001       (Anthropic, econômico)
#   claude-sonnet-4-6               (Anthropic, balanceado)
MODEL_ID = os.getenv("MODEL_ID", "gemini-2.5-flash-preview-04-17")

KNOWLEDGE_BASE_DIR = "knowledge"
VECTOR_DB_PATH = "data/lancedb"


def get_model():
    """Retorna o modelo correto baseado no MODEL_ID configurado."""
    if MODEL_ID.startswith("gemini"):
        from agno.models.google import Gemini
        return Gemini(id=MODEL_ID)
    else:
        from agno.models.anthropic import Claude
        return Claude(id=MODEL_ID)

