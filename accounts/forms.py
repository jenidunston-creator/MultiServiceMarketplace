from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User, CustomerProfile, ProviderProfile, Business, BusinessMember


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

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

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


class TeamMemberForm(forms.ModelForm):
    """The business owner types in the details of a team member. No account needed."""

    def __init__(self, *args, business=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.business = business

    class Meta:
        model = BusinessMember
        fields = ['full_name', 'position', 'email', 'phone']

    def clean_full_name(self):
        name = ' '.join(self.cleaned_data['full_name'].split())
        if len(name) < 2:
            raise forms.ValidationError('Please enter the full name.')
        if self.business and BusinessMember.objects.filter(
                business=self.business, full_name__iexact=name).exists():
            raise forms.ValidationError(f'{name} is already on your team.')
        return name

    def clean_position(self):
        return self.cleaned_data['position'].strip() or 'Team member'

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        if phone and not all(ch.isdigit() or ch in ' +-()' for ch in phone):
            raise forms.ValidationError('Use digits, spaces, + - and brackets only.')
        return phone
