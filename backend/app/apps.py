from django.apps import AppConfig


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.app'

    def ready(self):
        import backend.app.signals
        import sys

        # Evita registrar métricas durante collectstatic/migrate no build Docker.
        if any(cmd in sys.argv for cmd in ("collectstatic", "makemigrations")):
            return
        from backend.app.metrics import connect_auth_signals

        import backend.app.metrics  # noqa: F401

        connect_auth_signals()
