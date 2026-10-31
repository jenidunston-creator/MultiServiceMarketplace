from django import forms

from accounts.security import clean_public_text
from .models import Service, ServiceProviderService


class ServiceListingForm(forms.ModelForm):
    """The form a provider fills in to offer a service."""

    class Meta:
        model = ServiceProviderService
        fields = [
            'service', 'price', 'experience_years',
            'availability', 'description', 'image', 'is_active',
        ]
        labels = {
            'service': 'Service',
            'price': 'Price (NZD, incl. GST)',
            'experience_years': 'Years of experience',
            'is_active': 'Show this service to customers',
        }
        widgets = {
            'service': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'availability': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Mon to Sat, 8am to 5pm'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, provider=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.provider = provider
        # only show services that are switched on
        self.fields['service'].queryset = Service.objects.filter(is_active=True).order_by('name')

    def clean_description(self):
        return clean_public_text(self.cleaned_data['description'])

    def clean_availability(self):
        return clean_public_text(self.cleaned_data['availability'])

    def clean_price(self):
        price = self.cleaned_data['price']
        if price < 0:
            raise forms.ValidationError('Price cannot be negative.')
        return price

    def clean_service(self):
        # a provider can offer each service only once
        service = self.cleaned_data['service']
        if self.provider is not None:
            others = ServiceProviderService.objects.filter(
                provider=self.provider, service=service
            ).exclude(pk=self.instance.pk)
            if others.exists():
                raise forms.ValidationError('You already offer this service. Edit that one instead.')
        return service
