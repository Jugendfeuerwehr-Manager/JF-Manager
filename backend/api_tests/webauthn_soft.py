"""Software authenticator for tests: produces genuine WebAuthn responses.

Uses an EC P-256 key (COSE alg -7), "none" attestation and the same
encodings a browser sends (base64url JSON), so the server code path is the
real py_webauthn verification.
"""

import base64
import hashlib
import json
import os
import struct

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unb64url(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class SoftAuthenticator:
    def __init__(self, origin="http://localhost:5173", rp_id="localhost"):
        self.origin = origin
        self.rp_id = rp_id
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.credential_id = os.urandom(32)
        self.sign_count = 0

    def _cose_key(self):
        numbers = self.key.public_key().public_numbers()
        return cbor2.dumps({1: 2, 3: -7, -1: 1, -2: numbers.x.to_bytes(32, "big"), -3: numbers.y.to_bytes(32, "big")})

    def _client_data(self, kind, challenge, origin=None):
        return json.dumps(
            {"type": kind, "challenge": challenge, "origin": origin or self.origin, "crossOrigin": False}
        ).encode()

    def create(self, options, origin=None):
        """Answer navigator.credentials.create() options (dict from the API)."""
        rp_hash = hashlib.sha256(self.rp_id.encode()).digest()
        attested = bytes(16) + struct.pack(">H", len(self.credential_id)) + self.credential_id + self._cose_key()
        auth_data = rp_hash + bytes([0x45]) + struct.pack(">I", self.sign_count) + attested
        attestation = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth_data})
        client_data = self._client_data("webauthn.create", options["challenge"], origin)
        return {
            "id": b64url(self.credential_id),
            "rawId": b64url(self.credential_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": b64url(client_data),
                "attestationObject": b64url(attestation),
                "transports": ["internal"],
            },
            "clientExtensionResults": {},
        }

    def get(self, options, origin=None, counter_step=1, user_handle=None, user_verified=True):
        """Answer navigator.credentials.get() options.

        ``user_handle`` (bytes) is what a discoverable credential returns;
        ``user_verified=False`` models a key that only checked presence.
        """
        self.sign_count += counter_step
        rp_hash = hashlib.sha256(self.rp_id.encode()).digest()
        flags = 0x05 if user_verified else 0x01
        auth_data = rp_hash + bytes([flags]) + struct.pack(">I", self.sign_count)
        client_data = self._client_data("webauthn.get", options["challenge"], origin)
        signature = self.key.sign(auth_data + hashlib.sha256(client_data).digest(), ec.ECDSA(hashes.SHA256()))
        return {
            "id": b64url(self.credential_id),
            "rawId": b64url(self.credential_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": b64url(client_data),
                "authenticatorData": b64url(auth_data),
                "signature": b64url(signature),
                "userHandle": b64url(user_handle) if user_handle else None,
            },
            "clientExtensionResults": {},
        }
