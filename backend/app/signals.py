from django.db.models.signals import post_save
from django.dispatch import receiver
from backend.app.models.prefeitura import Prefeitura

@receiver(post_save, sender=Prefeitura)
def criar_secretarias_padrao(sender, instance: Prefeitura, created, **kwargs):
    if not created:
        return  # só na criação, não em updates
    instance.create_default_secretarias()
