import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse
from l4py.context import set_trace_id, set_user_id


class LoggingContextMiddleware:
    """Enriches every log line emitted while handling a request with a
    trace_id (propagated from the X-Trace-Id header, or generated) and the
    authenticated user's id, via l4py's context vars."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex
        set_trace_id(trace_id)
        # Literal session key, not imported from apps.authentication: apps/shared
        # must never import from a domain app.
        helix_user = request.session.get("helix_user")
        set_user_id(helix_user.get("sub") if helix_user else None)
        return self.get_response(request)
