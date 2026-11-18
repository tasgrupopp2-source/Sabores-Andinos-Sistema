from django.urls import path
from . import views

app_name = "pedidos"
urlpatterns = [
    # Clientes
    path("clientes/", views.ClienteListView.as_view(), name="clientes"),
    path("clientes/nuevo/", views.ClienteCreateView.as_view(), name="cliente_crear"),
    path("clientes/<int:pk>/", views.ClienteDetailView.as_view(), name="cliente_detalle"),
    path("clientes/<int:pk>/editar/", views.ClienteUpdateView.as_view(), name="cliente_editar"),
    # Pedidos
    path("", views.PedidoListView.as_view(), name="lista"),
    path("nuevo/", views.PedidoCreateView.as_view(), name="crear"),
    path("<int:pk>/", views.PedidoDetailView.as_view(), name="pedido_detalle"),
    path("<int:pk>/estado/", views.PedidoCambiarEstadoView.as_view(), name="cambiar_estado"),
    # Stock
    path("stock/alertas/", views.StockAlertasView.as_view(), name="stock_alertas"),
    path("stock/movimientos/", views.MovimientoStockListView.as_view(), name="movimientos"),
    path("stock/movimientos/nuevo/", views.MovimientoStockCreateView.as_view(), name="movimiento_crear"),
]
