from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User, CustomerProfile, ProviderProfile, Business
from .security import clean_public_text


# The signup page sends: customer / provider / business
# The database stores:   CUSTOMER / SERVICE_PROVIDER / BUSINESS
ROLE_MAP = {
    'customer': User.Role.CUSTOMER,
    'provider': User.Role.SERVICE_PROVIDER,
    'business': User.Role.BUSINESS,
}


class SignupForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[
            ('customer', 'Customer'),
            ('provider', 'Service provider'),
            ('business', 'Business'),
        ]
    )
    phone = forms.CharField(max_length=20, required=False)
    city = forms.CharField(max_length=100, required=False)
    website = forms.CharField(required=False)   # trap for spam robots (hidden on the page)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if not email:
            raise forms.ValidationError('An email address is required.')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_website(self):
        if self.cleaned_data.get('website'):
            raise forms.ValidationError('Spam check failed.')
        return ''

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data['role']
        user.role = ROLE_MAP[role]
        user.phone_number = self.cleaned_data['phone']

        if commit:
            user.save()
            city = self.cleaned_data['city']
            display_name = user.get_full_name() or user.username

            if role == 'customer':
                CustomerProfile.objects.create(user=user, city=city)
            elif role == 'provider':
                ProviderProfile.objects.create(
                    user=user, provider_name=display_name, city=city
                )
            else:
                Business.objects.create(
                    owner=user, business_name=f"{display_name} Business", city=city
                )
        return user


class ProviderProfileForm(forms.ModelForm):
    """Lets a provider fix their details after signing up."""

    class Meta:
        model = ProviderProfile
        fields = ['provider_name', 'city', 'postcode', 'service_area', 'address',
                  'experience_years', 'availability_status', 'bio', 'profile_image']
        labels = {
            'provider_name': 'Business or provider name',
            'city': 'City',
            'service_area': 'Service area (suburbs you cover)',
            'experience_years': 'Years of experience',
            'availability_status': 'Availability',
            'profile_image': 'Photo (optional)',
        }
        widgets = {
            'provider_name': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'list': 'nz-cities',
                                           'placeholder': 'e.g. Auckland'}),
            'postcode': forms.TextInput(attrs={'class': 'form-control'}),
            'service_area': forms.TextInput(attrs={'class': 'form-control',
                                                   'placeholder': 'e.g. Henderson, Newmarket, North Shore'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'availability_status': forms.Select(attrs={'class': 'form-select'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'profile_image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_city(self):
        return self.cleaned_data['city'].strip().title()

    def clean_bio(self):
        return clean_public_text(self.cleaned_data['bio'])
