"""Creates demo accounts and sample data so the project can be tried straight away.

Run it with:   python manage.py seed_demo
It is safe to run more than once (it never makes duplicates).
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.models import Business, CustomerProfile, ProviderProfile, User
from services.models import Service, ServiceCategory, ServiceProviderService

# The demo password is public (it is in the README), so it must never open an admin account on the live site.
# On the live site you can also set a different one:  os.environ['DEMO_PASSWORD'] = '...'
DEMO_PASSWORD = os.environ.get('DEMO_PASSWORD', 'Demo@12345')

CATEGORIES = {
    'Home Maintenance': [('Plumbing', 95), ('Electrical Work', 100),
                         ('Lawn Mowing & Gardens', 60), ('Painting', 50),
                         ('Gutter Cleaning', 150), ('House Washing', 220),
                         ('Window Cleaning', 120), ('Fencing & Decking', 90),
                         ('Handyman', 70), ('Pest Control', 140),
                         ('Rubbish Removal', 130),
                         ('Locksmith', 110), ('Appliance Repair', 95),
                         ('Tiling & Flooring', 85), ('Curtains & Blinds', 90),
                         ('Chimney & Fireplace Service', 160),
                         ('Drainage & Drain Unblocking', 130), ('Hot Water Cylinder Repair', 150),
                         ('Gasfitting', 120), ('Glazing & Window Repair', 140),
                         ('Garage Door Repair', 130), ('Asbestos Testing', 200),
                         ('Septic Tank Service', 250), ('Leak Detection', 160),
                         ('Spray Painting & Roof Painting', 70), ('Furniture Assembly', 60),
                         ('Door & Lock Repair', 90), ('Skylight Install', 350),
                         ('Bathroom Waterproofing', 160), ('Shower Screen Install', 130),
                         ('Wallpaper Hanging', 70), ('Mould Washing', 120)],
    'Energy & Healthy Homes': [('Heat Pump Install & Service', 160),
                               ('Insulation & Ventilation', 180),
                               ('Solar Panel Installation', 250),
                               ('EV Charger Installation', 300),
                               ('Mould & Damp Treatment', 200),
                               ('Home Energy Assessment', 150), ('Double Glazing', 400),
                               ('Battery & Backup Power', 350), ('Dehumidifier & Ventilation Fit', 120)],
    'Vehicle Services': [('Mobile Mechanic', 110), ('Car Servicing & WOF', 150),
                         ('Car Detailing', 120), ('Tyre Fitting & Wheel Alignment', 90),
                         ('Panel Beating & Paint', 300), ('Car Battery Replacement', 80),
                         ('Roadside Assistance', 90), ('Motorbike Servicing', 130),
                         ('Windscreen Repair', 110), ('Auto Electrician', 110)],
    'Cleaning': [('Regular House Clean', 45), ('End of Tenancy Clean', 280),
                 ('Carpet Cleaning', 140), ('Airbnb Turnover Clean', 110), ('Office & Commercial Cleaning', 90),
                 ('Oven & BBQ Cleaning', 90), ('Spring Clean', 220),
                 ('Upholstery Cleaning', 120), ('Post-Construction Clean', 260)],
    'Moving & Delivery': [('Furniture Removals', 120), ('Same Day Parcel Delivery', 15),
                          ('Man with a Van', 85),
                          ('Courier & Freight', 40), ('Storage Help', 70), ('Piano Moving', 250),
                          ('Rubbish & Hard Waste Pickup', 120), ('Cars & Vehicle Transport', 220)],
    'Technical': [('Computer & Wi-Fi Support', 80), ('Smart Home Setup', 110),
                  ('Website Help for Small Business', 150),
                  ('Phone & Laptop Repair', 90), ('CCTV & Alarm Installation', 280),
                  ('Data Recovery & Backup', 100), ('Printer & Network Setup', 85),
                  ('App & Software Development', 120), ('Cyber Security Check', 150)],
    'Business & Finance': [('Bookkeeping & GST Returns', 75), ('Payroll Services', 90),
                         ('Business Plan Help', 120), ('Social Media Management', 90),
                         ('Virtual Assistant', 45), ('Translation Services', 60), ('Tax Help for Sole Traders', 120)],
    'Pets': [('Dog Walking', 30), ('Cat Sitting', 25), ('Aquarium Maintenance', 60), ('Pet Sitting', 45), ('Mobile Dog Grooming', 85), ('Dog Training', 70),
                 ('Pet Boarding', 55), ('Mobile Vet Visit', 150), ('Pet Taxi', 50)],
    'Education': [('Tutoring (NCEA & School)', 50), ('Music Lessons', 55),
                  ('Driving Lessons', 65), ('English Language Lessons', 45),
                  ('Te Reo Maori Lessons', 50), ('Swimming Lessons', 40),
                  ('Language Lessons (Chinese, Hindi, Spanish)', 50), ('Coding for Kids', 45),
                  ('University Study Help', 60), ('Sports Coaching', 55)],
    'Health & Wellbeing': [('Mobile Massage', 100), ('Personal Training', 70),
                           ('Physiotherapy at Home', 110), ('Yoga & Pilates', 45),
                           ('Nutrition Coaching', 80), ('Counselling', 130),
                           ('Massage Therapy (Clinic)', 95), ('Osteopath & Chiropractor', 100),
                           ('Boxing & Fitness Classes', 30)],
    'Building & Construction': [('Builder (Renovations)', 90), ('Carpentry', 80),
                                ('Roofing', 120), ('Plastering & Gib Stopping', 75),
                                ('Concrete & Driveways', 100), ('Bathroom Renovation', 110),
                                ('Kitchen Renovation', 110), ('Building Consent Help', 130),
                                ('Architectural Drafting', 110), ('Scaffolding', 150),
                                ('Demolition', 180), ('Insulation Install', 100),
                                ('Garden Shed & Sleepout Build', 120), ('Deck Staining', 80)],
    'Outdoor & Rural': [('Tree Felling & Removal', 180), ('Section Clearing', 120),
                        ('Landscaping & Retaining Walls', 95), ('Irrigation & Water Tanks', 100),
                        ('Farm Fencing', 85), ('Firewood Delivery', 160),
                        ('Pool & Spa Maintenance', 90), ('Boat & Marine Services', 110), ('Weed Control & Spraying', 90),
                        ('Compost & Mulch Delivery', 110), ('Beekeeping & Honey Services', 70),
                        ('Greenhouse & Vege Garden Setup', 100)],
    'Family & Care': [('Babysitting & Nanny', 30), ('After School Care', 25),
                      ('Elderly Home Care', 45), ('Disability Support Worker', 40),
                      ('Meal Prep & Home Cooking', 60), ('Respite Care', 45),
                      ('Postnatal Doula Support', 60), ('Companion & Errands', 35),
                      ('Household Helper', 35)],
    'Events & Creative': [('Photographer', 250), ('Videographer', 300), ('DJ & Sound', 280),
                          ('Wedding Planner', 400), ('Graphic Design', 80),
                          ('Bouncy Castle & Party Hire', 150), ('Florist', 100),
                          ('Celebrant', 450), ('Wedding Hair & Makeup', 250),
                          ('Live Band & Musician', 350), ('Cake Maker', 90), ('Face Painter', 80), ('MC & Host', 300),
                          ('Photo Booth Hire', 250), ('Kids Party Entertainer', 180),
                          ('Marquee & Event Hire', 500)],
    'Personal': [('Event Help', 40), ('Mobile Hairdresser', 90), ('Catering', 200),
                 ('Makeup Artist', 120), ('Nail Technician', 70),
                 ('Barber (Mobile)', 45), ('Beauty Therapist', 80),
                 ('Eyelash & Brow', 85), ('Personal Stylist', 95),
                 ('Tailoring & Alterations', 40), ('Dry Cleaning Pickup', 25)],
}


class Command(BaseCommand):
    help = 'Create demo users, categories, services and sample listings.'

    def make_user(self, username, role, **extra):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'role': role, 'email': f'{username}@example.com', **extra})
        # always reset the password, so the demo login works even if the user already existed
        user.set_password(DEMO_PASSWORD)
        user.is_active = True
        # demo accounts count as fully verified, so the demo works straight away
        user.email_verified = user.phone_verified = user.id_verified = True
        user.save()
        return user

    def handle(self, *args, **options):
        # --- categories and services
        for category_name, services in CATEGORIES.items():
            category, _ = ServiceCategory.objects.get_or_create(name=category_name)
            for name, price in services:
                Service.objects.get_or_create(
                    category=category, name=name,
                    defaults={'base_price': price, 'description': f'{name} across New Zealand.'})

        # --- users
        # The demo admin is made ONLY on your own computer (DEBUG is on). On the live site an admin with a
        # public password would let anyone in. There, use createsuperuser or changepassword instead.
        if settings.DEBUG:
            self.make_user('admin', User.Role.ADMIN, is_staff=True, is_superuser=True,
                           first_name='Site', last_name='Admin')
        else:
            self.stdout.write(self.style.WARNING(
                'Live site: no demo admin was made or changed. Make your own with '
                '"python manage.py createsuperuser" (then set its role to Admin).'))
        customer = self.make_user('demo_customer', User.Role.CUSTOMER,
                                  first_name='Aroha', last_name='Customer')
        provider = self.make_user('demo_provider', User.Role.SERVICE_PROVIDER,
                                  first_name='Sam', last_name='Provider')
        owner = self.make_user('demo_business', User.Role.BUSINESS,
                               first_name='Bella', last_name='Business')

        CustomerProfile.objects.get_or_create(user=customer, defaults={'city': 'Auckland'})
        profile, _ = ProviderProfile.objects.get_or_create(
            user=provider,
            defaults={'provider_name': 'Sparkle Home Care', 'city': 'Auckland',
                      'service_area': 'Auckland Central, North Shore, West Auckland',
                      'experience_years': 6, 'bio': 'Friendly, reliable local team.',
                      'verification_status': ProviderProfile.VerificationStatus.VERIFIED})
        business, _ = Business.objects.get_or_create(
            owner=owner, defaults={'business_name': 'Bella Property Group', 'city': 'Auckland'})

        # --- demo providers. Each one offers ONLY services that fit its own business.
        # (username, business name, city, area, price factor, list of service names)
        providers = [
            ('demo_provider', 'Sparkle Home Care', 'Auckland', 'Auckland Central, North Shore, West Auckland', 1.0, [
                'Regular House Clean', 'End of Tenancy Clean', 'Carpet Cleaning', 'Airbnb Turnover Clean',
                'Office & Commercial Cleaning', 'Oven & BBQ Cleaning', 'Spring Clean', 'Upholstery Cleaning',
                'Post-Construction Clean', 'Window Cleaning', 'House Washing', 'Gutter Cleaning',
                'Mould Washing', 'Dry Cleaning Pickup']),
            ('demo_wellington', 'Harbour Plumbing Co.', 'Wellington', 'Wellington City, Hutt Valley', 1.05, [
                'Plumbing', 'Electrical Work', 'Gasfitting', 'Drainage & Drain Unblocking',
                'Hot Water Cylinder Repair', 'Leak Detection', 'Septic Tank Service',
                'Bathroom Waterproofing', 'Shower Screen Install', 'Appliance Repair',
                'Chimney & Fireplace Service']),
            ('demo_christchurch', 'Canterbury Home Services', 'Christchurch', 'Christchurch and Selwyn', 1.0, [
                'Painting', 'Spray Painting & Roof Painting', 'Wallpaper Hanging', 'Handyman',
                'Furniture Assembly', 'Door & Lock Repair', 'Garage Door Repair', 'Glazing & Window Repair',
                'Tiling & Flooring', 'Curtains & Blinds', 'Locksmith', 'Heat Pump Install & Service',
                'Insulation & Ventilation', 'Mould & Damp Treatment', 'Home Energy Assessment',
                'Dehumidifier & Ventilation Fit', 'Double Glazing', 'Skylight Install',
                'Pest Control', 'Asbestos Testing']),
            ('demo_hamilton', 'Waikato Garden & Property', 'Hamilton', 'Hamilton and Cambridge', 0.95, [
                'Lawn Mowing & Gardens', 'Fencing & Decking', 'Rubbish Removal', 'Tree Felling & Removal',
                'Section Clearing', 'Landscaping & Retaining Walls', 'Irrigation & Water Tanks',
                'Farm Fencing', 'Firewood Delivery', 'Pool & Spa Maintenance', 'Weed Control & Spraying',
                'Compost & Mulch Delivery', 'Beekeeping & Honey Services', 'Greenhouse & Vege Garden Setup']),
            ('demo_tauranga', 'Bay Mobile Care', 'Tauranga', 'Tauranga and Mount Maunganui', 1.0, [
                'Mobile Mechanic', 'Car Servicing & WOF', 'Car Detailing', 'Tyre Fitting & Wheel Alignment',
                'Panel Beating & Paint', 'Car Battery Replacement', 'Roadside Assistance',
                'Motorbike Servicing', 'Windscreen Repair', 'Auto Electrician', 'Boat & Marine Services']),
            ('demo_dunedin', 'Otago Cleaners & Movers', 'Dunedin', 'Dunedin and Mosgiel', 0.95, [
                'Regular House Clean', 'Carpet Cleaning', 'Furniture Removals', 'Man with a Van',
                'Same Day Parcel Delivery', 'Courier & Freight', 'Storage Help', 'Piano Moving',
                'Rubbish & Hard Waste Pickup', 'Cars & Vehicle Transport']),
            ('demo_queenstown', 'Southern Lakes Wellbeing & Events', 'Queenstown', 'Queenstown and Wanaka', 1.1, [
                'Mobile Massage', 'Personal Training', 'Physiotherapy at Home', 'Yoga & Pilates',
                'Nutrition Coaching', 'Counselling', 'Massage Therapy (Clinic)', 'Osteopath & Chiropractor',
                'Boxing & Fitness Classes', 'Photographer', 'Videographer', 'DJ & Sound', 'Wedding Planner',
                'Bouncy Castle & Party Hire', 'Florist', 'Celebrant', 'Live Band & Musician', 'Cake Maker',
                'Face Painter', 'MC & Host', 'Photo Booth Hire', 'Kids Party Entertainer',
                'Marquee & Event Hire', 'Event Help', 'Catering']),
            ('demo_rotorua', 'Rotorua Business Hub', 'Rotorua', 'Rotorua and Taupo', 0.95, [
                'Bookkeeping & GST Returns', 'Payroll Services', 'Business Plan Help',
                'Social Media Management', 'Virtual Assistant', 'Translation Services',
                'Tax Help for Sole Traders', 'Graphic Design', 'Website Help for Small Business',
                'App & Software Development', 'Cyber Security Check', 'Computer & Wi-Fi Support',
                'Printer & Network Setup', 'Data Recovery & Backup', 'Phone & Laptop Repair']),
            ('demo_nelson', 'Nelson Solar & Smart Home', 'Nelson', 'Nelson, Richmond and Motueka', 1.0, [
                'Solar Panel Installation', 'EV Charger Installation', 'Battery & Backup Power',
                'Smart Home Setup', 'CCTV & Alarm Installation']),
            ('demo_builder', 'Manawatu Builders & Roofing', 'Palmerston North', 'Palmerston North and Feilding', 1.0, [
                'Builder (Renovations)', 'Carpentry', 'Roofing', 'Plastering & Gib Stopping',
                'Concrete & Driveways', 'Bathroom Renovation', 'Kitchen Renovation', 'Building Consent Help',
                'Architectural Drafting', 'Scaffolding', 'Demolition', 'Insulation Install',
                'Garden Shed & Sleepout Build', 'Deck Staining']),
            ('demo_pets', 'Paws & Whiskers Pet Care', 'Napier', 'Napier and Hastings', 1.0, [
                'Dog Walking', 'Cat Sitting', 'Pet Sitting', 'Mobile Dog Grooming', 'Dog Training',
                'Pet Boarding', 'Mobile Vet Visit', 'Pet Taxi', 'Aquarium Maintenance']),
            ('demo_beauty', 'Glow Mobile Beauty', 'Wellington', 'Wellington and Lower Hutt', 1.0, [
                'Mobile Hairdresser', 'Makeup Artist', 'Wedding Hair & Makeup', 'Nail Technician',
                'Barber (Mobile)', 'Beauty Therapist', 'Eyelash & Brow', 'Personal Stylist',
                'Tailoring & Alterations']),
            ('demo_education', 'Otago Learning & Coaching', 'Dunedin', 'Dunedin and Mosgiel', 1.0, [
                'Tutoring (NCEA & School)', 'University Study Help', 'Music Lessons', 'Driving Lessons',
                'English Language Lessons', 'Te Reo Maori Lessons',
                'Language Lessons (Chinese, Hindi, Spanish)', 'Swimming Lessons', 'Coding for Kids',
                'Sports Coaching']),
            ('demo_family', 'Kind Hands Family Care', 'Christchurch', 'Christchurch and Selwyn', 1.0, [
                'Babysitting & Nanny', 'After School Care', 'Elderly Home Care', 'Disability Support Worker',
                'Meal Prep & Home Cooking', 'Respite Care', 'Postnatal Doula Support',
                'Companion & Errands', 'Household Helper']),
        ]

        demo_usernames = [p[0] for p in providers]
        category_of = {n: c for c, items in CATEGORIES.items() for n, _ in items}
        for username, biz_name, city, area, factor, offers in providers:
            if username == 'demo_provider':
                prof = profile
            else:
                user = self.make_user(username, User.Role.SERVICE_PROVIDER,
                                      first_name=biz_name.split()[0], last_name='Provider')
                prof, _ = ProviderProfile.objects.get_or_create(
                    user=user,
                    defaults={'provider_name': biz_name, 'city': city, 'service_area': area,
                              'experience_years': 5, 'bio': f'Trusted local team in {city}.',
                              'verification_status': ProviderProfile.VerificationStatus.VERIFIED})
            # remove old demo listings that do not suit this business
            prof.offered_services.exclude(service__name__in=offers).delete()
            for name in offers:
                # a name may exist twice in an older database: take the one in the right category
                matches = Service.objects.filter(name=name).order_by('id')
                service = matches.filter(category__name=category_of[name]).first() or matches.first()
                ServiceProviderService.objects.get_or_create(
                    provider=prof, service=service,
                    defaults={'price': round(float(service.base_price) * factor),
                              'experience_years': prof.experience_years or 5,
                              'availability': 'Monday to Saturday, 8am to 5pm',
                              'description': f'{name} by {prof.provider_name}. Friendly, reliable and fully insured.'})

        # check: every service in the catalogue is offered by at least one demo provider
        offered = {n for p in providers for n in p[5]}
        missing = [n for cat in CATEGORIES.values() for n, _ in cat if n not in offered]
        if missing:
            self.stdout.write(self.style.WARNING(f'Not offered by any demo provider: {missing}'))

        self.stdout.write(self.style.SUCCESS('Demo data is ready.'))
        self.stdout.write(f'Password for every demo account: {DEMO_PASSWORD}')
        self.stdout.write('Usernames: ' + ('admin, ' if settings.DEBUG else '') +
                          'demo_customer, demo_provider, demo_business '
                          '(plus ' + ', '.join(demo_usernames[1:]) + ')')
        self.stdout.write('Check the site now with:  python manage.py security_check')
