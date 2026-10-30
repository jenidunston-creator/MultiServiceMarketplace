"""Email, mobile and passport/visa checks. An admin gives the final approval for the documents."""
import hashlib
import hmac
import secrets
from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from communication.models import Notification
from communication.notify import notify, notify_admins
from . import security
from .decorators import role_required
from .models import IdentityVerification, PhoneCode, User

EMAIL_SALT = 'servana-email-verify'
MAX_FILE_MB = 5
ALLOWED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.pdf')


def hash_value(value):
    """One-way hash (HMAC) so we never keep the raw passport number or the raw code."""
    return hmac.new(settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()


# ------------------------------------------------------------------ the checklist page
@login_required
def verify_center(request):
    user = request.user
    identity = IdentityVerification.objects.filter(user=user).first()
    return render(request, 'accounts/verify.html', {
        'identity': identity,
        'demo': settings.DEMO_SHOW_CODES,
    })


# ------------------------------------------------------------------ 1. email
def build_email_link(request, user):
    token = signing.dumps({'uid': user.pk, 'email': user.email}, salt=EMAIL_SALT)
    return request.build_absolute_uri(reverse('verify_email_confirm', args=[token]))


@login_required
@require_POST
def verify_email_send(request):
    user = request.user
    if not user.email:
        messages.error(request, 'Your account has no email address. Please add one in the Django admin or sign up again.')
        return redirect('verify_center')
    if user.email_verified:
        return redirect('verify_center')
    if security.too_many(f'email-send:{user.pk}', 5, 3600):
        messages.error(request, 'Too many emails requested. Please wait an hour and try again.')
        return redirect('verify_center')

    link = build_email_link(request, user)
    send_mail('Confirm your Servana email',
              f'Hi {user.first_name or user.username},\n\nPlease confirm your email by opening this link:\n{link}\n\n'
              'The link works for 24 hours. If you did not create a Servana account, ignore this email.\n',
              settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
    messages.success(request, f'We sent a confirmation link to {user.email}.')
    if settings.DEMO_SHOW_CODES:
        messages.info(request, f'Demo mode (email is not connected): open this link to confirm: {link}')
    return redirect('verify_center')


def verify_email_confirm(request, token):
    try:
        data = signing.loads(token, salt=EMAIL_SALT, max_age=86400)
    except signing.BadSignature:
        messages.error(request, 'That link is not valid or has expired. Please request a new one.')
        return redirect('verify_center' if request.user.is_authenticated else 'login')
    user = User.objects.filter(pk=data.get('uid'), email=data.get('email')).first()
    if user is None:
        messages.error(request, 'That link is not valid.')
        return redirect('login')
    if not user.email_verified:
        user.email_verified = True
        user.save(update_fields=['email_verified'])
    messages.success(request, 'Your email is confirmed. Thank you!')
    return redirect('verify_center' if request.user.is_authenticated else 'login')


# ------------------------------------------------------------------ 2. mobile number
class PhoneForm(forms.Form):
    phone = forms.CharField(max_length=20, label='Mobile number')

    def clean_phone(self):
        raw = self.cleaned_data['phone']
        digits = ''.join(ch for ch in raw if ch.isdigit())
        if not 8 <= len(digits) <= 15:
            raise ValidationError('Please enter a valid mobile number with the country code, e.g. +64 21 123 4567.')
        return ('+' if raw.strip().startswith('+') else '') + digits


@login_required
@require_POST
def verify_phone_send(request):
    user = request.user
    form = PhoneForm(request.POST)
    if not form.is_valid():
        messages.error(request, form.errors['phone'][0])
        return redirect('verify_center')
    phone = form.cleaned_data['phone']

    if User.objects.filter(phone_number=phone, phone_verified=True).exclude(pk=user.pk).exists():
        messages.error(request, 'That mobile number is already used by another account.')
        return redirect('verify_center')
    if security.too_many(f'sms-send:{user.pk}', 5, 3600):
        messages.error(request, 'Too many codes requested. Please wait an hour and try again.')
        return redirect('verify_center')

    code = f'{secrets.randbelow(1000000):06d}'
    PhoneCode.objects.filter(user=user).delete()
    PhoneCode.objects.create(user=user, phone=phone, code_hash=hash_value(code),
                             expires_at=timezone.now() + timedelta(minutes=10))
    user.phone_number = phone
    user.phone_verified = False
    user.save(update_fields=['phone_number', 'phone_verified'])

    # A real SMS service (for example Twilio) would send the code here.
    messages.success(request, f'We sent a 6-digit code to {phone}. It works for 10 minutes.')
    if settings.DEMO_SHOW_CODES:
        messages.info(request, f'Demo mode (SMS is not connected): your code is {code}')
    return redirect('verify_center')


@login_required
@require_POST
def verify_phone_confirm(request):
    user = request.user
    entry = PhoneCode.objects.filter(user=user).order_by('-created_at').first()
    code = request.POST.get('code', '').strip()
    if entry is None or entry.expires_at < timezone.now():
        messages.error(request, 'That code has expired. Please request a new one.')
        return redirect('verify_center')
    if entry.attempts >= 5:
        messages.error(request, 'Too many wrong tries. Please request a new code.')
        return redirect('verify_center')
    entry.attempts += 1
    entry.save(update_fields=['attempts'])
    if not hmac.compare_digest(entry.code_hash, hash_value(code)):
        messages.error(request, 'That code is not correct.')
        return redirect('verify_center')

    user.phone_verified = True
    user.save(update_fields=['phone_verified'])
    entry.delete()
    messages.success(request, 'Your mobile number is confirmed.')
    return redirect('verify_center')


# ------------------------------------------------------------------ 3. passport and visa
def check_file(upload):
    if upload is None:
        return upload
    name = upload.name.lower()
    if not name.endswith(ALLOWED_EXTENSIONS):
        raise ValidationError('Please upload a JPG, PNG or PDF file.')
    if upload.size > MAX_FILE_MB * 1024 * 1024:
        raise ValidationError(f'The file is too big. Maximum size is {MAX_FILE_MB} MB.')
    return upload


class IdentityForm(forms.Form):
    full_name = forms.CharField(max_length=150, label='Full name exactly as on the passport')
    nationality = forms.CharField(max_length=80)
    document_type = forms.ChoiceField(choices=IdentityVerification.DocumentType.choices, label='Document')
    passport_number = forms.CharField(max_length=20, label='Passport number',
                                      help_text='We keep only a scrambled (hashed) copy of this number.')
    passport_expiry = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label='Passport expiry date')
    passport_image = forms.FileField(label='Photo or scan of the passport photo page')
    visa_type = forms.CharField(max_length=60, required=False, label='NZ visa type',
                                help_text='For example Resident, Work, Student. Not needed for a NZ passport.')
    visa_expiry = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}),
                                  label='Visa expiry date')
    visa_image = forms.FileField(required=False, label='Photo or scan of the NZ visa')
    agree = forms.BooleanField(label='I agree that Servana can store these documents to check my identity.')

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'

    def clean_passport_image(self):
        return check_file(self.cleaned_data.get('passport_image'))

    def clean_visa_image(self):
        return check_file(self.cleaned_data.get('visa_image'))

    def clean_passport_expiry(self):
        value = self.cleaned_data['passport_expiry']
        if value <= timezone.localdate():
            raise ValidationError('This passport has expired.')
        return value

    def clean_passport_number(self):
        number = ''.join(ch for ch in self.cleaned_data['passport_number'] if ch.isalnum()).upper()
        if len(number) < 6:
            raise ValidationError('Please enter the full passport number.')
        # one passport = one account
        duplicate = IdentityVerification.objects.filter(passport_hash=hash_value(number)).exclude(
            user=self.user).exists()
        if duplicate:
            raise ValidationError('This passport is already used by another account.')
        return number

    def clean(self):
        data = super().clean()
        if data.get('document_type') == IdentityVerification.DocumentType.OTHER_PASSPORT:
            today = timezone.localdate()
            if not data.get('visa_type'):
                self.add_error('visa_type', 'Please enter your NZ visa type.')
            if not data.get('visa_expiry'):
                self.add_error('visa_expiry', 'Please enter the visa expiry date.')
            elif data['visa_expiry'] <= today:
                self.add_error('visa_expiry', 'This visa has expired, so it is not valid in New Zealand.')
            if not data.get('visa_image'):
                self.add_error('visa_image', 'Please upload your NZ visa.')
        return data


@login_required
def verify_identity(request):
    user = request.user
    existing = IdentityVerification.objects.filter(user=user).first()
    if existing and existing.status in (IdentityVerification.Status.PENDING, IdentityVerification.Status.APPROVED):
        messages.info(request, 'Your documents are already ' + existing.get_status_display().lower() + '.')
        return redirect('verify_center')

    if request.method == 'POST':
        form = IdentityForm(request.POST, request.FILES, user=user)
        if security.too_many(f'id-submit:{user.pk}', 10, 3600):
            messages.error(request, 'Too many tries. Please wait an hour.')
            return redirect('verify_center')
        if form.is_valid():
            d = form.cleaned_data
            nz = d['document_type'] == IdentityVerification.DocumentType.NZ_PASSPORT
            record = existing or IdentityVerification(user=user)
            record.full_name = d['full_name']
            record.nationality = d['nationality']
            record.document_type = d['document_type']
            record.passport_hash = hash_value(d['passport_number'])
            record.passport_expiry = d['passport_expiry']
            record.passport_image = d['passport_image']
            record.visa_type = '' if nz else d['visa_type']
            record.visa_expiry = None if nz else d['visa_expiry']
            if not nz:
                record.visa_image = d['visa_image']
            record.status = IdentityVerification.Status.PENDING
            record.admin_note = ''
            record.reviewed_by = None
            record.reviewed_at = None
            record.save()
            user.id_verified = False
            user.save(update_fields=['id_verified'])
            notify_admins(Notification.NotificationType.GENERAL, 'New ID check',
                          f'{user.username} sent passport and visa details to check.', '/dashboard/admin-panel/verifications/')
            messages.success(request, 'Thank you! An admin will check your documents.')
            return redirect('verify_center')
    else:
        form = IdentityForm(user=user)
    return render(request, 'accounts/verify_identity.html', {'form': form, 'existing': existing})


@login_required
def identity_document(request, pk, which):
    """Only the owner and admins can open a passport or visa photo."""
    record = get_object_or_404(IdentityVerification, pk=pk)
    is_admin = request.user.is_superuser or request.user.role == User.Role.ADMIN
    if not (is_admin or record.user_id == request.user.pk):
        raise Http404
    field = {'passport': record.passport_image, 'visa': record.visa_image}.get(which)
    if not field:
        raise Http404
    response = FileResponse(field.open('rb'))
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


# ------------------------------------------------------------------ admin review
@role_required(User.Role.ADMIN)
def admin_verifications(request):
    records = IdentityVerification.objects.select_related('user')
    return render(request, 'accounts/admin_verifications.html', {
        'waiting': records.filter(status=IdentityVerification.Status.PENDING).order_by('submitted_at'),
        'history': records.exclude(status=IdentityVerification.Status.PENDING).order_by('-reviewed_at')[:30],
    })


@role_required(User.Role.ADMIN)
@require_POST
def admin_verification_decide(request, pk):
    record = get_object_or_404(IdentityVerification.objects.select_related('user'), pk=pk)
    decision = request.POST.get('decision')
    note = request.POST.get('note', '').strip()[:255]
    if record.status != IdentityVerification.Status.PENDING:
        messages.info(request, 'That check was already decided.')
        return redirect('admin_verifications')

    if decision == 'approve':
        today = timezone.localdate()
        if record.passport_expiry <= today or (record.visa_expiry and record.visa_expiry <= today):
            messages.error(request, 'A document has expired. Please reject this check instead.')
            return redirect('admin_verifications')
        record.status = IdentityVerification.Status.APPROVED
        record.user.id_verified = True
        text = 'Your passport and visa were approved.'
    elif decision == 'reject':
        record.status = IdentityVerification.Status.REJECTED
        record.user.id_verified = False
        text = 'Your documents were rejected.' + (f' Reason: {note}' if note else ' Please send them again.')
    else:
        messages.error(request, 'Please choose approve or reject.')
        return redirect('admin_verifications')

    record.admin_note = note
    record.reviewed_by = request.user
    record.reviewed_at = timezone.now()
    record.save()
    record.user.save(update_fields=['id_verified'])
    notify(record.user, Notification.NotificationType.GENERAL, 'ID check result', text, '/accounts/verify/')
    messages.success(request, f'{record.user.username}: {record.get_status_display().lower()}.')
    return redirect('admin_verifications')
