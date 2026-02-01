"""
Stream API profiler - measures per-stage timing and efficiency for SSE stream endpoints.

Fully decoupled: HTTP client only, no imports from server/core/services.
"""

from .profiler import profile_one, ProfileResult
from .endpoints import STREAM_ENDPOINTS, StreamEndpoint

__all__ = ["profile_one", "ProfileResult", "STREAM_ENDPOINTS", "StreamEndpoint"]
