from django.conf import settings
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path


def healthz(request):
    """Liveness/readiness probe for the hosting platform."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:
        return JsonResponse({'status': 'error', 'database': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('healthz/', healthz),
    path(settings.ADMIN_URL, admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/dealers/', include('dealers.urls')),
    path('api/gas/', include('gas.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/payments/', include('payments.urls')),
]
