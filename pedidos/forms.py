from django import forms
from django.forms import inlineformset_factory

from catalogo.models import Producto
from .models import Cliente, Pedido, DetallePedido, MovimientoStock


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ("nombre", "apellido", "documento", "telefono", "email", "direccion")

    def clean_documento(self):
        doc = self.cleaned_data["documento"].strip()
        if (
            Cliente.objects.filter(documento__iexact=doc)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError("Ya existe un cliente con ese documento.")
        return doc


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ("cliente", "observaciones")
        widgets = {"observaciones": forms.Textarea(attrs={"rows": 3})}


class DetallePedidoForm(forms.ModelForm):
    class Meta:
        model = DetallePedido
        fields = ("producto", "cantidad")

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get("cantidad")
        if cantidad is not None and cantidad < 1:
            raise forms.ValidationError("La cantidad debe ser al menos 1.")
        return cantidad


DetallePedidoFormSet = inlineformset_factory(
    Pedido,
    DetallePedido,
    form=DetallePedidoForm,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class CambiarEstadoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ("estado",)


class MovimientoStockForm(forms.ModelForm):
    class Meta:
        model = MovimientoStock
        fields = ("producto", "tipo", "cantidad", "motivo")

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get("cantidad")
        if cantidad is not None and cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a cero.")
        return cantidad
