"""Controles de segurança para autenticação (troca de senha, sessões)."""
from __future__ import annotations

from django.core.cache import cache
from django.utils import timezone

PWD_CHANGE_FAILED_KEY = "pwd_change_failed:{key}"
PWD_CHANGE_LOCK_KEY = "pwd_change_lock:{key}"
PWD_CHANGE_MAX_ATTEMPTS = 5
PWD_CHANGE_LOCK_MINUTES = 15
PASSWORD_MAX_LENGTH = 128


def password_change_lock_key_ip(ip: str) -> str:
    return f"ip:{ip}"


def password_change_lock_key_user(user_id) -> str:
    return f"user:{user_id}"


def record_password_change_failed_attempt(key: str) -> int:
    k = PWD_CHANGE_FAILED_KEY.format(key=key)
    cnt = cache.get(k, 0) + 1
    cache.set(k, cnt, timeout=PWD_CHANGE_LOCK_MINUTES * 60)
    if cnt >= PWD_CHANGE_MAX_ATTEMPTS:
        cache.set(PWD_CHANGE_LOCK_KEY.format(key=key), True, timeout=PWD_CHANGE_LOCK_MINUTES * 60)
    return cnt


def clear_password_change_attempts(key: str) -> None:
    cache.delete(PWD_CHANGE_FAILED_KEY.format(key=key))
    cache.delete(PWD_CHANGE_LOCK_KEY.format(key=key))


def is_password_change_locked(key: str) -> bool:
    return bool(cache.get(PWD_CHANGE_LOCK_KEY.format(key=key), False))


def invalidate_other_user_sessions(user, *, keep_session_key: str | None) -> int:
    """
    Encerra sessões Django de outros browsers/dispositivos do mesmo usuário.
    Requer backend de sessão em banco (default Django).
    """
    try:
        from django.contrib.sessions.models import Session
    except ImportError:
        return 0

    user_id = str(user.pk)
    removed = 0
    now = timezone.now()
    for session in Session.objects.filter(expire_date__gte=now).only("session_key", "session_data", "expire_date"):
        if keep_session_key and session.session_key == keep_session_key:
            continue
        try:
            if session.get_decoded().get("_auth_user_id") == user_id:
                session.delete()
                removed += 1
        except Exception:
            continue
    return removed
