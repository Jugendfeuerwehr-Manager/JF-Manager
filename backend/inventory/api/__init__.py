"""Inventory DRF API package.

Provides structured serializers & viewsets replacing ad-hoc JSON views in
`inventory.api_views` and legacy viewsets in `inventory.views`.

Migration strategy:
1. Introduce parallel DRF endpoints (stable, typed, discoverable).
2. Keep old AJAX endpoints temporarily (marked deprecated) to avoid breaking UI.
3. Gradually migrate frontend JS to new `/api/v1/inventory/...` endpoints.
"""
