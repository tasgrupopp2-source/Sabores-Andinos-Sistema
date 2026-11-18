from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q, F
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    TemplateView,
)

from catalogo.models import Producto
from .forms import (
    ClienteForm,
    PedidoForm,
    DetallePedidoFormSet,
    CambiarEstadoForm,
    MovimientoStockForm,
)
from .models import Cliente, Pedido, DetallePedido, MovimientoStock


# ── Clientes ──

class ClienteListView(LoginRequiredMixin, ListView):
    model = Cliente
    template_name = "pedidos/cliente_lista.html"
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()[:100]
        if q:
            qs = qs.filter(
                Q(nombre__icontains=q)
                | Q(apellido__icontains=q)
                | Q(documento__icontains=q)
            )
        return qs


class ClienteDetailView(LoginRequiredMixin, DetailView):
    model = Cliente
    template_name = "pedidos/cliente_detalle.html"


class ClienteCreateView(LoginRequiredMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "pedidos/cliente_form.html"


class ClienteUpdateView(LoginRequiredMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "pedidos/cliente_form.html"


# ── Pedidos ──

class PedidoListView(LoginRequiredMixin, ListView):
    model = Pedido
    template_name = "pedidos/pedido_lista.html"
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset().select_related("cliente", "creado_por")
        estado = self.request.GET.get("estado", "").strip()
        if estado in dict(Pedido.Estado.choices):
            qs = qs.filter(estado=estado)
        return qs


class PedidoDetailView(LoginRequiredMixin, DetailView):
    model = Pedido
    template_name = "pedidos/pedido_detalle.html"

    def get_queryset(self):
        return super().get_queryset().select_related("cliente", "creado_por").prefetch_related("detalles__producto")


class PedidoCreateView(LoginRequiredMixin, CreateView):
    model = Pedido
    form_class = PedidoForm
    template_name = "pedidos/pedido_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset"] = DetallePedidoFormSet(self.request.POST)
        else:
            ctx["formset"] = DetallePedidoFormSet()
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]
        if not formset.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            form.instance.creado_por = self.request.user
            self.object = form.save()
            formset.instance = self.object
            detalles = formset.save(commit=False)
            for detalle in detalles:
                detalle.precio_unitario = detalle.producto.precio
                detalle.save()
            for obj in formset.deleted_objects:
                obj.delete()
        messages.success(self.request, f"Pedido #{self.object.pk} creado.")
        return redirect(self.object.get_absolute_url())


class PedidoCambiarEstadoView(LoginRequiredMixin, UpdateView):
    model = Pedido
    form_class = CambiarEstadoForm
    template_name = "pedidos/pedido_cambiar_estado.html"

    def form_valid(self, form):
        pedido = form.save(commit=False)
        nuevo_estado = pedido.estado
        with transaction.atomic():
            if nuevo_estado == Pedido.Estado.EN_PREPARACION:
                for detalle in pedido.detalles.select_related("producto"):
                    prod = detalle.producto
                    if prod.stock < detalle.cantidad:
                        messages.error(
                            self.request,
                            f"Stock insuficiente de {prod.nombre}: hay {prod.stock}, se necesitan {detalle.cantidad}.",
                        )
                        return redirect(pedido.get_absolute_url())
                    prod.stock = F("stock") - detalle.cantidad
                    prod.save(update_fields=["stock"])
                    MovimientoStock.objects.create(
                        producto=prod,
                        tipo=MovimientoStock.Tipo.SALIDA,
                        cantidad=detalle.cantidad,
                        motivo=f"Pedido #{pedido.pk}",
                        pedido=pedido,
                        registrado_por=self.request.user,
                    )
            elif nuevo_estado == Pedido.Estado.CANCELADO:
                for detalle in pedido.detalles.select_related("producto"):
                    prod = detalle.producto
                    prod.stock = F("stock") + detalle.cantidad
                    prod.save(update_fields=["stock"])
                    MovimientoStock.objects.create(
                        producto=prod,
                        tipo=MovimientoStock.Tipo.ENTRADA,
                        cantidad=detalle.cantidad,
                        motivo=f"Cancelación pedido #{pedido.pk}",
                        pedido=pedido,
                        registrado_por=self.request.user,
                    )
            pedido.save()
        messages.success(self.request, f"Pedido #{pedido.pk} → {pedido.get_estado_display()}.")
        return redirect(pedido.get_absolute_url())


# ── Stock ──

class StockAlertasView(LoginRequiredMixin, ListView):
    template_name = "pedidos/stock_alertas.html"
    paginate_by = 20

    def get_queryset(self):
        minimo = int(self.request.GET.get("minimo", 10))
        return Producto.objects.filter(stock__lte=minimo).select_related("categoria").order_by("stock")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["minimo"] = self.request.GET.get("minimo", 10)
        return ctx


class MovimientoStockListView(LoginRequiredMixin, ListView):
    model = MovimientoStock
    template_name = "pedidos/movimiento_lista.html"
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().select_related("producto", "registrado_por", "pedido")


class MovimientoStockCreateView(LoginRequiredMixin, CreateView):
    model = MovimientoStock
    form_class = MovimientoStockForm
    template_name = "pedidos/movimiento_form.html"
    success_url = reverse_lazy("pedidos:movimientos")

    def form_valid(self, form):
        mov = form.save(commit=False)
        mov.registrado_por = self.request.user
        with transaction.atomic():
            prod = mov.producto
            if mov.tipo == MovimientoStock.Tipo.ENTRADA:
                prod.stock = F("stock") + mov.cantidad
            elif mov.tipo == MovimientoStock.Tipo.SALIDA:
                prod.refresh_from_db()
                if prod.stock < mov.cantidad:
                    form.add_error("cantidad", "Stock insuficiente.")
                    return self.form_invalid(form)
                prod.stock = F("stock") - mov.cantidad
            else:
                prod.stock = mov.cantidad
            prod.save(update_fields=["stock"])
            mov.save()
        messages.success(self.request, "Movimiento registrado.")
        return redirect(self.success_url)
