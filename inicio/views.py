from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from catalogo.models import Producto, Categoria
from cuentas.models import Usuario
from pedidos.models import Cliente, Pedido


@login_required
def home(request):
    return render(
        request,
        "inicio/home.html",
        {
            "productos": Producto.objects.count(),
            "categorias": Categoria.objects.count(),
            "clientes": Cliente.objects.count(),
            "pedidos_count": Pedido.objects.exclude(estado="cancelado").count(),
            "pendientes": (
                Usuario.objects.filter(estado="pendiente").count()
                if request.user.is_superuser
                else None
            ),
            "recientes": Producto.objects.select_related("categoria").order_by(
                "-actualizado"
            )[:5],
            "stock_bajo": Producto.objects.filter(stock__lte=10).count(),
        },
    )


def salud(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"estado": "no disponible"}, status=503)
    return JsonResponse({"estado": "ok"})
