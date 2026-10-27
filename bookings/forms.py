from django import forms
from django.utils import timezone

from services.models import ServiceRequest
from .models import Complaint, Payment, Quotation, Review


class RequestForm(forms.ModelForm):
    """Used for both 'Book now' and 'Request a quote'."""

    class Meta:
        model = ServiceRequest
        fields = ['preferred_date', 'preferred_time', 'location', 'city',
                  'postcode', 'urgency', 'description']
        labels = {
            'preferred_date': 'Preferred date',
            'preferred_time': 'Preferred time',
            'location': 'Service address',
            'city': 'City',
            'postcode': 'Postcode',
            'urgency': 'Urgency',
            'description': 'Describe what you need',
        }
        widgets = {
            'preferred_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'preferred_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street and suburb'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'postcode': forms.TextInput(attrs={'class': 'form-control'}),
            'urgency': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'e.g. 3 bedroom home, two bathrooms, pets at home'}),
        }

    def clean_preferred_date(self):
        date = self.cleaned_data['preferred_date']
        if date < timezone.localdate():
            raise forms.ValidationError('Please choose today or a future date.')
        return date


class QuotationForm(forms.ModelForm):
    class Meta:
        model = Quotation
        fields = ['amount', 'proposed_date', 'proposed_time', 'message']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01',
                                               'placeholder': 'Total price (NZD)'}),
            'proposed_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'proposed_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                                             'placeholder': 'What is included?'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError('The price must be more than 0.')
        return amount


class PaymentForm(forms.Form):
    method = forms.ChoiceField(
        choices=Payment.Method.choices,
        initial=Payment.Method.CARD,                      # the card option starts ticked
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        error_messages={'required': 'Please choose a payment method.'},
    )


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=[(5, '5 - Excellent'), (4, '4 - Good'), (3, '3 - Okay'),
                 (2, '2 - Poor'), (1, '1 - Terrible')],
        coerce=int,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['category', 'subject', 'description']
        labels = {'category': 'What went wrong?', 'subject': 'Short title',
                  'description': 'Tell us what happened'}
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 150}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }

    def clean_description(self):
        text = self.cleaned_data['description'].strip()
        if len(text) < 10:
            raise forms.ValidationError('Please give a little more detail (at least 10 characters).')
        return text
