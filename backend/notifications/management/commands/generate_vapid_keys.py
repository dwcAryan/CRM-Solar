import re
from pathlib import Path

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from django.conf import settings
from django.core.management.base import BaseCommand
from py_vapid import Vapid, b64urlencode


class Command(BaseCommand):
    help = "Generates a new VAPID key pair for Web Push notifications and saves them to backend/.env."

    def handle(self, *args, **options):
        v = Vapid()
        v.generate_keys()

        raw_pub = v.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        pub_key = b64urlencode(raw_pub)
        priv_pem = v.private_pem().decode('utf-8').strip()

        self.stdout.write(self.style.SUCCESS("Generated fresh VAPID key pair:"))
        self.stdout.write(f"  Public Key:  {pub_key}")

        env_file = Path(settings.BASE_DIR) / '.env'
        if env_file.exists():
            content = env_file.read_text(encoding='utf-8')
            if 'VAPID_PUBLIC_KEY=' in content:
                content = re.sub(r'VAPID_PUBLIC_KEY=.*', f'VAPID_PUBLIC_KEY={pub_key}', content)
            else:
                content += f"\nVAPID_PUBLIC_KEY={pub_key}"

            if 'VAPID_ADMIN_EMAIL=' not in content:
                content += "\nVAPID_ADMIN_EMAIL=admin@solarcrm.com"

            # Single-line escaped PEM or raw
            escaped_pem = priv_pem.replace('\n', '\\n')
            if 'VAPID_PRIVATE_KEY=' in content:
                content = re.sub(r'VAPID_PRIVATE_KEY=.*', f'VAPID_PRIVATE_KEY="{escaped_pem}"', content)
            else:
                content += f'\nVAPID_PRIVATE_KEY="{escaped_pem}"\n'

            env_file.write_text(content, encoding='utf-8')
            self.stdout.write(self.style.SUCCESS(f"Updated VAPID configuration in {env_file}"))
        else:
            self.stdout.write(self.style.WARNING("backend/.env not found; keys displayed above."))
