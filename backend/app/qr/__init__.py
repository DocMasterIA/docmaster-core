"""
Módulo reutilizável de QR Code (imagem PNG e URLs públicas).

Uso típico: embutir PNG em PDF/HTML via ``png.qr_png_data_url`` e codificar
URLs absolutas com ``public_url.build_public_absolute_url``.
"""

from backend.app.qr.png import qr_png_data_url
from backend.app.qr.public_url import build_public_absolute_url, resolve_public_api_base_url

__all__ = [
    "qr_png_data_url",
    "build_public_absolute_url",
    "resolve_public_api_base_url",
]
