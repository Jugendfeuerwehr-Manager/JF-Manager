"""Renderer for binary download actions."""

import json

from rest_framework.renderers import BaseRenderer


class PassthroughRenderer(BaseRenderer):
    """Return file bytes as-is; error details still go out as JSON for the client."""

    media_type = "*/*"
    format = "binary"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if isinstance(data, (dict, list)):
            response = (renderer_context or {}).get("response")
            if response is not None:
                response["Content-Type"] = "application/json"
            return json.dumps(data, ensure_ascii=False).encode("utf-8")
        return data
