from __future__ import annotations

import os

import logfire

_configured = False


def configure_logfire(service: str = "agl") -> None:
    """Configure Logfire once. It sends only when this project's own AGL_LOGFIRE_TOKEN is set; any ambient
    LOGFIRE_TOKEN is dropped so no other project's credentials are ever loaded or used. With no token it is a
    local no-op that sends nothing.
    """
    global _configured
    if _configured:
        return
    token = os.getenv("AGL_LOGFIRE_TOKEN")
    if not token:
        os.environ.pop("LOGFIRE_TOKEN", None)
    logfire.configure(service_name=service, token=token, send_to_logfire=bool(token), console=False)
    logfire.instrument_pydantic_ai(include_content=False)
    _configured = True
