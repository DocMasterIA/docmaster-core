"""Geração de QR Code como data URL PNG (embutir em HTML/PDF)."""
from __future__ import annotations

import base64
import io


def qr_png_data_url(
    payload: str,
    *,
    box_size: int = 3,
    border: int = 1,
    fill_color: str = "#1f4e79",
    back_color: str = "white",
) -> str:
    """Devolve ``data:image/png;base64,...`` para uso em ``<img src=...>``."""
    import qrcode

    qr = qrcode.QRCode(
        version=None,
        box_size=box_size,
        border=border,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill_color, back_color=back_color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"
