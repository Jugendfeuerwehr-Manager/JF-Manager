"""
OIDC authentication views for JF-Manager.

These views implement the backend-side of the OIDC Authorization Code Flow
and bridge mozilla-django-oidc with the simplejwt token system used by the
Vue 3 frontend — without exposing the client_secret to the browser.

Flow:
  1. Frontend calls GET /api/v1/auth/oidc/public-config/
     → Returns { enabled, provider_name, hide_local_login }
  2. Frontend calls GET /api/v1/auth/oidc/login/?next=/dashboard
     → Backend builds authorization_url with state/nonce stored in cache
     → Returns { authorization_url }
  3. Browser is redirected to IdP → user authenticates → IdP redirects back to
     GET /api/v1/auth/oidc/callback/?code=...&state=...
     → Backend exchanges code for tokens, authenticates user, issues simplejwt tokens
     → Stores {access, refresh} under a short-lived exchange_code in cache
     → Redirects browser to {FRONTEND_URL}/auth/oidc/callback?exchange_code=<uuid>
  4. Frontend OIDCCallbackView POSTs exchange_code to
     POST /api/v1/auth/oidc/exchange/
     → Returns { access, refresh } (consumed, one-time use)
"""

import json
import logging
import secrets
import uuid
from urllib.parse import quote, urlencode, urlparse

import requests
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.views import View
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("users.oidc_views")

# How long (seconds) the state/nonce stay valid
OIDC_STATE_TIMEOUT = 300  # 5 minutes

# How long (seconds) the exchange_code → token pair stays in cache
OIDC_EXCHANGE_TIMEOUT = 60  # 1 minute


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_oidc_config():
    from settings_manager.models import OIDCConfig

    return OIDCConfig.get_or_create_default()


def _validate_oidc_url(url: str, label: str = "URL", *, allowed_host: str | None = None) -> str:
    """
    Validate that a URL used for outbound OIDC requests is safe:
      - Must be https:// (no http, file, ftp, …)
      - Must have a non-empty netloc (no bare paths or localhost tricks)
      - If allowed_host is provided, the URL's hostname must match it exactly
        (prevents the discovery document from redirecting JWKS to a different server).

    Returns the validated URL unchanged.
    Raises ValueError with a descriptive message on failure.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"OIDC {label} muss ein HTTPS-URL sein (erhalten: {parsed.scheme!r}).")
    if not parsed.netloc:
        raise ValueError(f"OIDC {label} hat keinen gültigen Host.")
    if allowed_host is not None and parsed.hostname != allowed_host:
        raise ValueError(
            f"OIDC {label} zeigt auf einen anderen Host ({parsed.hostname!r}) als der"
            f" konfigurierte Issuer ({allowed_host!r}). Anfrage abgelehnt."
        )
    return url


def _fetch_discovery_document(issuer_url: str) -> dict:
    """
    Fetch the OIDC Discovery Document from {issuer_url}/.well-known/openid-configuration.
    Returns the parsed JSON dict.
    Raises requests.RequestException on network errors or non-200 responses.
    """
    _validate_oidc_url(issuer_url, "Issuer-URL")
    issuer_host = urlparse(issuer_url).hostname
    discovery_url = issuer_url.rstrip("/") + "/.well-known/openid-configuration"
    # Re-validate the constructed URL to prevent SSRF: must be HTTPS and on the
    # same host as the configured issuer (guards against path-traversal tricks).
    _validate_oidc_url(discovery_url, "Discovery-URL", allowed_host=issuer_host)
    logger.debug("Fetching OIDC discovery document from %s", discovery_url)
    response = requests.get(discovery_url, timeout=10)
    response.raise_for_status()
    return response.json()


def _verify_id_token(id_token: str, discovery: dict, config, nonce: str) -> dict:
    """
    Verify the id_token JWT signature using the provider's JWKS and return claims.

    Uses PyJWT (already available via djangorestframework-simplejwt) so we do
    not rely on mozilla-django-oidc's internal URL resolution or settings access.
    """
    import jwt as pyjwt

    jwks_uri = discovery.get("jwks_uri", "")
    if not jwks_uri:
        raise ValueError("OIDC Provider hat keine jwks_uri im Discovery-Dokument.")

    # Validate jwks_uri: must be HTTPS and on the same host as the issuer to
    # prevent a malicious discovery document from redirecting key-fetches to an
    # attacker-controlled server (SSRF / key-confusion).
    issuer_host = urlparse(config.issuer_url).hostname
    _validate_oidc_url(jwks_uri, "JWKS-URI", allowed_host=issuer_host)

    jwks_response = requests.get(jwks_uri, timeout=10)
    jwks_response.raise_for_status()
    jwks = jwks_response.json()

    # Decode header without verification to find the signing key.
    header = pyjwt.get_unverified_header(id_token)
    kid = header.get("kid")
    alg = header.get("alg", "RS256")

    matching_key = None
    for key_data in jwks.get("keys", []):
        if kid is None or key_data.get("kid") == kid:
            if alg.startswith("RS"):
                matching_key = pyjwt.algorithms.RSAAlgorithm.from_jwk(key_data)
            elif alg.startswith("EC"):
                matching_key = pyjwt.algorithms.ECAlgorithm.from_jwk(key_data)
            else:
                matching_key = pyjwt.algorithms.RSAAlgorithm.from_jwk(key_data)
            break

    if matching_key is None:
        raise ValueError(f"Kein passender JWK-Schl\u00fcssel f\u00fcr kid={kid!r} gefunden.")

    claims = pyjwt.decode(
        id_token,
        key=matching_key,
        algorithms=[alg],
        audience=config.client_id,
    )

    # Verify issuer (lenient about trailing slash differences).
    token_issuer = claims.get("iss", "").rstrip("/")
    expected_issuer = config.issuer_url.rstrip("/")
    if token_issuer != expected_issuer:
        raise ValueError(f"Issuer stimmt nicht \u00fcberein: {token_issuer!r} != {expected_issuer!r}")

    # Verify nonce.
    if claims.get("nonce") != nonce:
        raise ValueError("Nonce stimmt nicht \u00fcberein.")

    logger.debug("OIDC: id_token verified for sub='%s' issuer='%s'", claims.get("sub", ""), token_issuer)
    return claims


def _build_debug_info(claims: dict, config) -> dict:
    """
    Extract non-sensitive claim fields for display on the error page.
    Helps admins verify which user/groups Nextcloud sent vs. what is configured.
    """
    groups = claims.get(config.groups_claim, [])
    if isinstance(groups, str):
        groups = [g.strip() for g in groups.split(",") if g.strip()]

    sub = claims.get("sub", "")
    sub_display = sub[:12] + "…" if len(sub) > 12 else sub

    return {
        "email": claims.get("email", ""),
        "name": claims.get("name", claims.get("preferred_username", "")),
        "sub": sub_display,
        "issuer": claims.get("iss", ""),
        "groups_claim": config.groups_claim,
        "groups": groups if isinstance(groups, list) else [],
    }


# ---------------------------------------------------------------------------
# Public config endpoint (no auth required — called by login page)
# ---------------------------------------------------------------------------


class OIDCPublicConfigView(APIView):
    """
    GET /api/v1/auth/oidc/public-config/

    Returns the minimum OIDC configuration that the frontend needs to decide
    whether to show the SSO button and/or hide local login.
    Does NOT return any secrets.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        config = _get_oidc_config()
        return Response(
            {
                "enabled": config.enabled,
                "provider_name": config.provider_name,
                "hide_local_login": config.hide_local_login,
            }
        )


# ---------------------------------------------------------------------------
# OIDC login initiation (generates authorization URL)
# ---------------------------------------------------------------------------


class OIDCLoginView(APIView):
    """
    GET /api/v1/auth/oidc/login/?next=/dashboard

    Builds the OIDC authorization URL with a fresh state + nonce.
    State and nonce are stored in the Django cache for later verification.

    Returns: { authorization_url: "https://provider/authorize?..." }
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        config = _get_oidc_config()
        if not config.enabled:
            return Response(
                {"detail": "OIDC ist nicht aktiviert."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            discovery = _fetch_discovery_document(config.issuer_url)
        except Exception as exc:
            logger.error("OIDC: Failed to fetch discovery document: %s", exc)
            return Response(
                {"detail": "OIDC Provider nicht erreichbar. Bitte versuche es später erneut."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        authorization_endpoint = discovery.get("authorization_endpoint")
        if not authorization_endpoint:
            return Response(
                {"detail": "OIDC Provider hat keinen authorization_endpoint."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)

        # Store state → nonce in cache so callback can verify
        next_url = request.GET.get("next", "/")
        cache.set(
            f"oidc_state_{state}",
            {"nonce": nonce, "next": next_url},
            OIDC_STATE_TIMEOUT,
        )

        # Build callback URL — always points to our backend callback view
        callback_url = request.build_absolute_uri("/api/v1/auth/oidc/callback/")

        params = {
            "response_type": "code",
            "client_id": config.client_id,
            "redirect_uri": callback_url,
            "scope": config.scope,
            "state": state,
            "nonce": nonce,
        }
        authorization_url = authorization_endpoint + "?" + urlencode(params)

        logger.debug(
            "OIDC: generated authorization URL for provider '%s' (state=%s)",
            config.provider_name,
            state[:8] + "...",
        )
        return Response({"authorization_url": authorization_url})


# ---------------------------------------------------------------------------
# OIDC callback (handles IdP redirect, issues simplejwt tokens)
# ---------------------------------------------------------------------------


class OIDCCallbackView(View):
    """
    GET /api/v1/auth/oidc/callback/?code=...&state=...

    This is a plain Django view (not a DRF APIView) because it needs to:
    - Handle a browser redirect from the IdP (not an AJAX request)
    - Issue an HTTP redirect back to the frontend

    Process:
    1. Validate state (CSRF protection)
    2. Exchange code for tokens via IdP token endpoint
    3. Authenticate user (creates/updates via JFManagerOIDCBackend)
    4. Issue simplejwt access + refresh tokens
    5. Store them under a short-lived exchange_code in cache
    6. Redirect browser to {FRONTEND_URL}/auth/oidc/callback?exchange_code=...
    """

    def get(self, request):
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")

        # --- Error from IdP ---
        if "error" in request.GET:
            error = request.GET.get("error", "unknown_error")
            error_description = request.GET.get("error_description", "")
            logger.warning("OIDC: IdP returned error '%s': %s", error, error_description)
            return self._redirect_to_frontend_error(frontend_url, f"IdP-Fehler: {error}")

        code = request.GET.get("code")
        state = request.GET.get("state")

        if not code or not state:
            logger.warning("OIDC callback: missing code or state parameter")
            return self._redirect_to_frontend_error(frontend_url, "Ungültige OIDC-Antwort (fehlende Parameter).")

        # --- Validate state ---
        state_data = cache.get(f"oidc_state_{state}")
        if not state_data:
            logger.warning("OIDC callback: unknown or expired state '%s'", state[:8] + "...")
            return self._redirect_to_frontend_error(frontend_url, "Sitzung abgelaufen. Bitte erneut anmelden.")
        cache.delete(f"oidc_state_{state}")

        nonce = state_data.get("nonce")
        next_url = state_data.get("next", "/")

        config = _get_oidc_config()
        if not config.enabled:
            return self._redirect_to_frontend_error(frontend_url, "OIDC ist deaktiviert.")

        # --- Fetch discovery document ---
        try:
            discovery = _fetch_discovery_document(config.issuer_url)
        except Exception as exc:
            logger.error("OIDC callback: failed to fetch discovery document: %s", exc)
            return self._redirect_to_frontend_error(frontend_url, "OIDC Provider nicht erreichbar.")

        token_endpoint = discovery.get("token_endpoint")
        if not token_endpoint:
            return self._redirect_to_frontend_error(frontend_url, "OIDC Provider hat keinen token_endpoint.")

        # --- Exchange authorization code for tokens ---
        callback_url = request.build_absolute_uri("/api/v1/auth/oidc/callback/")
        try:
            token_response = requests.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": callback_url,
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                },
                timeout=15,
            )
            token_response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("OIDC callback: token exchange failed: %s", exc)
            return self._redirect_to_frontend_error(frontend_url, "Token-Austausch fehlgeschlagen.")

        token_data = token_response.json()
        id_token = token_data.get("id_token")

        if not id_token:
            logger.error("OIDC callback: no id_token in token response")
            return self._redirect_to_frontend_error(frontend_url, "Kein ID-Token erhalten.")

        # --- Verify id_token signature and extract claims ---
        try:
            claims = _verify_id_token(id_token, discovery, config, nonce)
        except Exception as exc:
            logger.warning("OIDC callback: id_token verification failed: %s", exc)
            return self._redirect_to_frontend_error(frontend_url, f"ID-Token Verifikation fehlgeschlagen: {exc}")

        debug_info = _build_debug_info(claims, config)

        # --- Create/update user via OIDC backend ---
        try:
            from users.oidc_backend import JFManagerOIDCBackend

            backend = JFManagerOIDCBackend()
            # Store pre-decoded claims; authenticate() reads them instead of
            # re-exchanging the already-consumed authorization code.
            request._oidc_claims = claims
            user = backend.authenticate(request)
        except Exception as exc:
            logger.warning("OIDC callback: authentication failed: %s", exc)
            return self._redirect_to_frontend_error(frontend_url, str(exc), debug=debug_info)

        if user is None:
            logger.warning("OIDC callback: backend returned None (user not authenticated)")
            return self._redirect_to_frontend_error(
                frontend_url,
                "Anmeldung fehlgeschlagen. Bitte überprüfe dein Konto.",
                debug=debug_info,
            )

        # --- Issue simplejwt tokens ---
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        jwt_access = str(refresh.access_token)
        jwt_refresh = str(refresh)

        # Store tokens under a one-time exchange code
        exchange_code = str(uuid.uuid4())
        cache.set(
            f"oidc_exchange_{exchange_code}",
            {"access": jwt_access, "refresh": jwt_refresh, "next": next_url},
            OIDC_EXCHANGE_TIMEOUT,
        )

        logger.info(
            "OIDC: user '%s' authenticated successfully via provider '%s'",
            user.username,
            config.provider_name,
        )

        redirect_url = f"{frontend_url}/auth/oidc/callback?exchange_code={exchange_code}"
        response = HttpResponse(status=302)
        response["Location"] = redirect_url
        return response

    @staticmethod
    def _redirect_to_frontend_error(frontend_url: str, message: str, debug: dict | None = None) -> HttpResponse:
        redirect_url = f"{frontend_url}/auth/oidc/callback?error={quote(message)}"
        if debug:
            redirect_url += f"&debug={quote(json.dumps(debug, ensure_ascii=False))}"
        response = HttpResponse(status=302)
        response["Location"] = redirect_url
        return response


# ---------------------------------------------------------------------------
# Token exchange (one-time, consumes exchange_code from cache)
# ---------------------------------------------------------------------------


class OIDCTokenExchangeView(APIView):
    """
    POST /api/v1/auth/oidc/exchange/
    Body: { "exchange_code": "<uuid>" }

    Returns: { "access": "...", "refresh": "...", "next": "/..." }

    This is the only endpoint the frontend JS calls after the OIDC callback.
    The exchange_code is one-time and expires after OIDC_EXCHANGE_TIMEOUT seconds.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        exchange_code = request.data.get("exchange_code", "")
        if not exchange_code:
            return Response(
                {"detail": "exchange_code fehlt."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = f"oidc_exchange_{exchange_code}"
        token_data = cache.get(cache_key)
        if not token_data:
            logger.warning("OIDC exchange: unknown or expired exchange_code '%s'", exchange_code[:8] + "...")
            return Response(
                {"detail": "Ungültiger oder abgelaufener Exchange-Code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # One-time use — delete immediately
        cache.delete(cache_key)
        logger.debug("OIDC exchange: tokens issued for exchange_code '%s'", exchange_code[:8] + "...")

        return Response(
            {
                "access": token_data["access"],
                "refresh": token_data["refresh"],
                "next": token_data.get("next", "/"),
            }
        )


# ---------------------------------------------------------------------------
# Discovery test (settings UI helper — requires change_oidc_settings)
# ---------------------------------------------------------------------------


class OIDCTestDiscoveryView(APIView):
    """
    POST /api/v1/auth/oidc/test-discovery/
    Body: { "issuer_url": "https://..." }

    Tests whether the OIDC Discovery Document can be fetched from the given
    issuer URL. Returns the discovery data or an error description.
    Requires change_oidc_settings or change_all_settings permission.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not (
            request.user.has_perm("settings_manager.change_oidc_settings")
            or request.user.has_perm("settings_manager.change_all_settings")
            or request.user.is_staff
        ):
            return Response(
                {"detail": "Keine Berechtigung."},
                status=status.HTTP_403_FORBIDDEN,
            )

        issuer_url = request.data.get("issuer_url", "").strip()
        if not issuer_url:
            return Response(
                {"detail": "issuer_url fehlt."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            discovery = _fetch_discovery_document(issuer_url)
        except requests.RequestException as exc:
            logger.warning("OIDC test-discovery: failed for '%s': %s", issuer_url, exc)
            return Response(
                {
                    "ok": False,
                    "detail": f"Discovery-Dokument konnte nicht abgerufen werden: {exc}",
                },
                status=status.HTTP_200_OK,
            )

        logger.info("OIDC test-discovery: success for '%s'", issuer_url)
        return Response(
            {
                "ok": True,
                "issuer": discovery.get("issuer"),
                "authorization_endpoint": discovery.get("authorization_endpoint"),
                "token_endpoint": discovery.get("token_endpoint"),
                "userinfo_endpoint": discovery.get("userinfo_endpoint"),
                "jwks_uri": discovery.get("jwks_uri"),
                "scopes_supported": discovery.get("scopes_supported", []),
                "claims_supported": discovery.get("claims_supported", []),
            }
        )
