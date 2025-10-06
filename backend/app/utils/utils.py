from django.core.cache import cache
from django.utils import timezone
import datetime

FAILED_KEY = "login_failed:{key}"        # key: ip or user:{username}
LOCK_KEY   = "login_lock:{key}"
MAX_ATTEMPTS = 6
LOCK_MINUTES = 15

def get_client_ip(request):
    # Simples — ajustar conforme proxy/nginx (X-Forwarded-For)
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")

def record_failed_attempt(key):
    k = FAILED_KEY.format(key=key)
    cnt = cache.get(k, 0) + 1
    cache.set(k, cnt, timeout=LOCK_MINUTES * 60)
    if cnt >= MAX_ATTEMPTS:
        cache.set(LOCK_KEY.format(key=key), True, timeout=LOCK_MINUTES * 60)
    return cnt

def clear_failed_attempts(key):
    cache.delete(FAILED_KEY.format(key=key))
    cache.delete(LOCK_KEY.format(key=key))

def is_locked(key):
    return cache.get(LOCK_KEY.format(key=key), False)
