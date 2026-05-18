from django.apps import AppConfig


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.app'

    def ready(self):
        import backend.app.signals
        # Registra contadores/histogramas docmaster_* no processo (Gunicorn multiprocess).
        import backend.app.metrics  # noqa: F401
