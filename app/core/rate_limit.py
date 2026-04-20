"""
Rate limiting configuration using slowapi.
Limiter is attached to FastAPI app.state and applied via decorators on endpoints.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
