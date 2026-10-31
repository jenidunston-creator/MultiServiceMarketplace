"""A plain-English safety check of the site. Run it on your computer AND on the live site:

    python manage.py security_check
"""
import os

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from accounts.models import IdentityVerification, User

# the demo password that is written in the README (and the one set in DEMO_PASSWORD, if any)
DEMO_PASSWORDS = {'Demo@12345', os.environ.get('DEMO_PASSWORD', 'Demo@12345')}


class Command(BaseCommand):
    help = 'Checks the site for the most common safety mistakes.'

    def ok(self, text):
        self.stdout.write(self.style.SUCCESS('OK       ' + text))

    def warn(self, text):
        self.stdout.write(self.style.WARNING('WARNING  ' + text))

    def danger(self, text):
        self.stdout.write(self.style.ERROR('DANGER   ' + text))

    def handle(self, *args, **options):
        self.stdout.write('Servana safety check\n')

        # 1. admin accounts that still use a password everyone can read
        powerful = User.objects.filter(is_active=True).filter(
            Q(is_superuser=True) | Q(is_staff=True) | Q(role=User.Role.ADMIN))
        bad = [u.username for u in powerful
               if any(check_password(pw, u.password) for pw in DEMO_PASSWORDS)]
        if bad:
            self.danger('These admin accounts use the public demo password, so anyone can log in as them: '
                        + ', '.join(bad))
            for name in bad:
                self.stdout.write(f'          fix:  python manage.py changepassword {name}')
        else:
            self.ok('No admin account uses the public demo password.')

        # 2. people with Django admin power who are not Servana admins
        odd = [u.username for u in User.objects.filter(is_active=True).filter(is_superuser=True)
               .exclude(role=User.Role.ADMIN)]
        if odd:
            self.warn('These accounts have full Django admin power but their role is not Admin: '
                      + ', '.join(odd) + '. Set the role to Admin, or switch off "superuser status".')
        else:
            self.ok('Every superuser has the Admin role.')

        # 3. settings for the live site
        if settings.DEBUG:
            self.warn('DEBUG is ON. This is fine on your own computer, but it must be OFF on the live site '
                      '(os.environ[\'DEBUG\'] = \'False\' in the WSGI file).')
        else:
            self.ok('DEBUG is off.')
        if settings.SECRET_KEY.startswith('django-insecure'):
            self.warn('SECRET_KEY is the default one from the code. On the live site set your own long secret.')
        else:
            self.ok('SECRET_KEY is a private one.')
        if settings.DEMO_SHOW_CODES:
            self.warn('Demo mode is ON: email links and phone codes are shown on the page, so anyone can pass '
                      'those two checks. The admin approval of the passport/visa is what protects the site. '
                      'For real use connect a real SMS/email service and set DEMO_SHOW_CODES=False.')
        else:
            self.ok('Email and phone codes are not shown on the page.')
        key = settings.STRIPE_SECRET_KEY
        if not key:
            self.warn('No Stripe key is set, so payments are switched off here.')
        elif key.startswith('sk_test_'):
            self.ok('Stripe is in TEST mode (no real money).')
        else:
            self.danger('The Stripe key is not a test key. Servana only accepts sk_test_ keys.')

        # 4. documents
        today = timezone.localdate()
        expired = [r.user.username for r in IdentityVerification.objects.filter(
            status=IdentityVerification.Status.APPROVED).select_related('user')
            if r.passport_expiry <= today or (r.visa_expiry and r.visa_expiry <= today)]
        if expired:
            self.warn('Approved passports/visas that have now expired (these users are blocked until they send '
                      'new ones): ' + ', '.join(expired))
        else:
            self.ok('No approved passport or visa has expired.')
        waiting = IdentityVerification.objects.filter(status=IdentityVerification.Status.PENDING).count()
        self.stdout.write(f'INFO     {waiting} passport/visa check(s) waiting for an admin.')
        never_sent = User.objects.filter(is_active=True, id_verified=True).exclude(
            role=User.Role.ADMIN).exclude(is_superuser=True).filter(identity__isnull=True)
        names = list(never_sent.values_list('username', flat=True))
        demo = [n for n in names if n.startswith('demo_')]
        others = [n for n in names if not n.startswith('demo_')]
        self.stdout.write(f'INFO     {len(demo)} demo account(s) are marked verified without sending a passport (demo only).')
        if others:
            self.warn('These accounts are marked verified but never sent a passport: ' + ', '.join(others)
                      + '. Remove them before real users arrive, or ask them to send documents.')
        else:
            self.ok('No other account skipped the passport check.')

