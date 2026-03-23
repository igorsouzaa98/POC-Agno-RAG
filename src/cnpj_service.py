"""
Serviço de verificação e processamento de CNPJ.

- Extração de CNPJ de texto/PDF (via pypdf)
- Validação de formato
- Verificação de inadimplência (stub para POC)
- Verificação de sessão ativa no SQLite
- Indexação do documento no LanceDB
"""
import re
import io
import sqlite3
import tempfile
import os
from typing import Optional

from pypdf import PdfReader

# CNPJs marcados como inadimplentes no stub (para testes e demo)
_INADIMPLENTES_STUB = {
    "00000000000000",  # CNPJ reservado para simular inadimplência em testes
}

# CNPJs marcados como em atendimento no stub (para testes e demo)
_EM_ATENDIMENTO_STUB = {
    "11111111000191",  # CNPJ reservado para simular atendimento ativo em testes
}


class CnpjService:
    def __init__(self, db_path: str = "data/agent_sessions.db"):
        self._db_path = db_path

    # ─── Validação ───────────────────────────────────────────────────────────

    def validate_cnpj(self, cnpj: str) -> bool:
        """Valida formato do CNPJ (14 dígitos, aceita pontuação)."""
        digits = re.sub(r"\D", "", cnpj)
        return len(digits) == 14

    def normalize_cnpj(self, cnpj: str) -> str:
        """Remove pontuação e retorna apenas 14 dígitos."""
        return re.sub(r"\D", "", cnpj)

    # ─── Extração ────────────────────────────────────────────────────────────

    def extract_cnpj_from_text(self, text: str) -> Optional[str]:
        """Encontra o primeiro CNPJ válido no texto."""
        pattern = r"\d{2}[\.\s]?\d{3}[\.\s]?\d{3}[\/\s]?\d{4}[\-\s]?\d{2}"
        match = re.search(pattern, text)
        if match:
            return self.normalize_cnpj(match.group())
        return None

    def extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """Extrai todo o texto de um PDF em bytes."""
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)

    def extract_cnpj_from_pdf(self, file_bytes: bytes) -> Optional[str]:
        """Extrai CNPJ de um PDF enviado como bytes."""
        text = self.extract_text_from_pdf(file_bytes)
        return self.extract_cnpj_from_text(text)

    # ─── Verificações ────────────────────────────────────────────────────────

    def check_inadimplencia(self, cnpj: str) -> dict:
        """
        Stub: verifica inadimplência do CNPJ.

        Em produção substituir por chamada a Serasa/BigDataCorp/ReceitaFederal.
        Por ora usa lista fixa de CNPJs bloqueados para demo.
        """
        normalized = self.normalize_cnpj(cnpj)
        inadimplente = normalized in _INADIMPLENTES_STUB
        return {
            "inadimplente": inadimplente,
            "fonte": "stub",
            "detalhes": (
                "CNPJ com restrições financeiras (simulado)"
                if inadimplente
                else "Sem restrições encontradas (simulado)"
            ),
        }

    def check_active_session(self, cnpj: str) -> dict:
        """
        Verifica se o CNPJ já tem uma sessão ativa no banco de sessões.

        Primeiro consulta o stub de CNPJs em atendimento (para testes e demo).
        Em seguida busca nas sessões das últimas 24h que contenham o CNPJ nos dados de runs.
        """
        normalized = self.normalize_cnpj(cnpj)
        if normalized in _EM_ATENDIMENTO_STUB:
            return {"em_atendimento": True, "session_id": "stub"}
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT session_id FROM agno_sessions
                WHERE (runs LIKE ? OR session_data LIKE ?)
                AND updated_at > (strftime('%s', 'now') - 86400) * 1000
                LIMIT 1
                """,
                (f"%{normalized}%", f"%{normalized}%"),
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return {"em_atendimento": True, "session_id": row[0]}
        except Exception:
            pass
        return {"em_atendimento": False, "session_id": None}

    # ─── Indexação ───────────────────────────────────────────────────────────

    def index_cnpj_document(self, cnpj: str, file_bytes: bytes) -> None:
        """
        Indexa o documento de CNPJ no banco vetorial (LanceDB).

        Salva o PDF temporariamente e usa o knowledge builder para indexar.
        """
        from src.knowledge_builder import get_knowledge_base

        normalized = self.normalize_cnpj(cnpj)
        kb = get_knowledge_base()

        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            prefix=f"cnpj_{normalized}_",
            delete=False,
        ) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            kb.insert(
                path=tmp_path,
                name=f"cnpj_{normalized}",
                upsert=True,
                skip_if_exists=False,
            )
        finally:
            os.unlink(tmp_path)
