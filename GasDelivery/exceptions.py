from rest_framework.views import exception_handler


def _first_message(data):
    """Pull a single human-readable message out of a DRF error payload."""
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return _first_message(data[0]) if data else None
    if isinstance(data, dict):
        if 'detail' in data:
            return _first_message(data['detail'])
        for key, value in data.items():
            message = _first_message(value)
            if message:
                return message if key == 'non_field_errors' else f'{key}: {message}'
    return None


def api_exception_handler(exc, context):
    """
    DRF's default handler, plus a top-level "error" string on every error response.

    The mobile app and admin dashboard read `response['error']`, so every error
    (validation, auth, throttling, 404...) carries one, while the original
    field-level errors are kept alongside it.
    """
    response = exception_handler(exc, context)
    if response is not None and isinstance(response.data, dict) and 'error' not in response.data:
        message = _first_message(response.data)
        if message:
            response.data['error'] = str(message)
    return response
