"""
Cópia do PDF de relatório PNCP para verificação via QR (download idêntico ao impresso).

Cada geração grava ``{sessao_id}/{token}.pdf`` + metadados; o token vai na URL do QR.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.utils import timezone


def issue_verification_token() -> str:
    return str(uuid.uuid4())


def _verification_root() -> Path:
    root = Path(settings.MEDIA_ROOT) / "pncp_relatorio_verification"
    root.mkdir(parents=True, exist_ok=True)
    return root


def verification_download_path(sessao_id: int, token: str) -> str:
    """Path relativo à API (sem host) para o endpoint de download."""
    return (
        f"/api/pncp/cotacoes/research/sessions/{int(sessao_id)}"
        f"/relatorio/verificacao/{token}/download"
    )


def _pdf_path(sessao_id: int, token: str) -> Path:
    safe = str(token).replace("/", "").replace("\\", "")
    d = _verification_root() / str(int(sessao_id))
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{safe}.pdf"


def _meta_path(sessao_id: int, token: str) -> Path:
    return _pdf_path(sessao_id, token).with_suffix(".meta.json")


def save_verification_pdf(
    *,
    sessao_id: int,
    token: str,
    pdf_bytes: bytes,
    filename: str,
) -> None:
    pdf_path = _pdf_path(sessao_id, token)
    meta_path = _meta_path(sessao_id, token)
    pdf_path.write_bytes(pdf_bytes)
    meta: Dict[str, Any] = {
        "sessao_id": int(sessao_id),
        "token": token,
        "filename": filename,
        "saved_at": timezone.now().isoformat(),
        "size_bytes": len(pdf_bytes),
    }
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    _prune_old_verification_copies(sessao_id, keep_token=token)


def _prune_old_verification_copies(sessao_id: int, *, keep_token: str) -> None:
    max_copies = int(getattr(settings, "PNCP_RELATORIO_VERIFICATION_MAX_COPIES", 8) or 0)
    if max_copies <= 0:
        return
    d = _verification_root() / str(int(sessao_id))
    if not d.is_dir():
        return
    metas = []
    for meta_path in d.glob("*.meta.json"):
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            saved_at = str(data.get("saved_at") or "")
            token = str(data.get("token") or meta_path.name.replace(".meta.json", ""))
            metas.append((saved_at, token, meta_path))
        except Exception:
            continue
    metas.sort(key=lambda x: x[0], reverse=True)
    for _saved_at, token, meta_path in metas[max_copies:]:
        if token == keep_token:
            continue
        try:
            meta_path.unlink(missing_ok=True)
            _pdf_path(sessao_id, token).unlink(missing_ok=True)
        except OSError:
            pass


def load_verification_pdf(sessao_id: int, token: str) -> Optional[Tuple[bytes, str]]:
    pdf_path = _pdf_path(sessao_id, token)
    if not pdf_path.is_file():
        return None
    meta_path = _meta_path(sessao_id, token)
    filename = "relatorio-verificacao.pdf"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if int(meta.get("sessao_id", 0)) != int(sessao_id):
                return None
            filename = str(meta.get("filename") or filename)
        except Exception:
            pass
    return pdf_path.read_bytes(), filename
