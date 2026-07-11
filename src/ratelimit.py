from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter, keyed by client IP. In-memory by default (fine for a single
# process / boilerplate); point `storage_uri` at Redis for multi-worker deploys.
limiter = Limiter(key_func=get_remote_address)
