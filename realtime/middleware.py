from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _user_from_token(raw_token):
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken, TokenError

    auth = JWTAuthentication()
    try:
        validated = auth.get_validated_token(raw_token)
        user = auth.get_user(validated)
    except (InvalidToken, TokenError, AuthenticationFailed):
        return AnonymousUser()
    return user if user.is_active else AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Authenticate WebSocket connections with a SimpleJWT access token, passed
    either as `?token=<access>` or as an `Authorization: Bearer <access>` header.
    """

    async def __call__(self, scope, receive, send):
        token = None

        query = parse_qs(scope.get('query_string', b'').decode())
        if query.get('token'):
            token = query['token'][0]
        else:
            for name, value in scope.get('headers', []):
                if name == b'authorization':
                    parts = value.decode().split()
                    if len(parts) == 2 and parts[0].lower() == 'bearer':
                        token = parts[1]
                    break

        scope['user'] = await _user_from_token(token) if token else AnonymousUser()
        return await super().__call__(scope, receive, send)
