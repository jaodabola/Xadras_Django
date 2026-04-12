from django.apps import AppConfig


class TournamentsConfig(AppConfig):
    # XADRAS - Configuração da App de Torneios
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tournaments'
    verbose_name = 'Tournament Management'
