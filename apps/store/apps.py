from django.apps import AppConfig


class StoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.store'
    verbose_name = 'Loja Virtual'

    def ready(self):
        try:
            import apps.store.signals  # noqa
        except ImportError:
            pass 