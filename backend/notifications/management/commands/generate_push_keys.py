import base64

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate a VAPID key pair for .env; keep the private key secret and stable."

    def handle(self, *args, **options):
        key = ec.generate_private_key(ec.SECP256R1())
        private = key.private_numbers().private_value.to_bytes(32, "big")
        public = key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)

        def encode(value):
            return base64.urlsafe_b64encode(value).rstrip(b"=").decode()

        self.stdout.write("WEB_PUSH_PUBLIC_KEY=" + encode(public))
        self.stdout.write("WEB_PUSH_PRIVATE_KEY=" + encode(private))
