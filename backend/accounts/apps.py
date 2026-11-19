import os
from django.apps import AppConfig
from django.core.checks import Error, Tags, register


def check_demo_accounts_in_production(app_configs, **kwargs):
    errors = []
    if os.getenv('APP_ENV', '').lower() == 'production':
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            demo_count = User.objects.filter(is_demo=True).count()
            if demo_count > 0:
                errors.append(
                    Error(
                        f"Found {demo_count} demo user accounts in production environment (is_demo=True). "
                        "Run `python manage.py remove_demo_data` to purge all demo accounts before deploying.",
                        id='accounts.E001',
                        hint='Remove all demo users and data in production.',
                    )
                )
        except Exception:
            # During early startup / pre-migrations
            pass
    return errors


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        register(Tags.security)(check_demo_accounts_in_production)
