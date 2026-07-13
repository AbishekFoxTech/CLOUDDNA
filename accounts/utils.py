from django.conf import settings
from django.core.cache import cache


def _cache_key(identifier):
    return f'login_attempts:{identifier}'


def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def is_locked_out(identifier):
    return cache.get(_cache_key(identifier), 0) >= settings.LOGIN_ATTEMPTS_LIMIT


def register_failed_attempt(identifier):
    key = _cache_key(identifier)
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, timeout=settings.LOGIN_ATTEMPTS_TIMEOUT)
    return attempts


def reset_attempts(identifier):
    cache.delete(_cache_key(identifier))


def remaining_lockout_seconds(identifier):
    key = _cache_key(identifier)
    ttl = cache.ttl(key) if hasattr(cache, 'ttl') else None
    return ttl or settings.LOGIN_ATTEMPTS_TIMEOUT
