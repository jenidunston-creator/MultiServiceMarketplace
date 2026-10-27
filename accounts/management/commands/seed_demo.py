"""Creates demo accounts and sample data so the project can be tried straight away.

Run it with:   python manage.py seed_demo
It is safe to run more than once (it never makes duplicates).
"""
from django.core.management.base import BaseCommand

from accounts.models import Business, BusinessMember, CustomerProfile, ProviderProfile, User
from services.models import Service, ServiceCategory, ServiceProviderService

DEMO_PASSWORD = 'Demo@12345'

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
        admin = self.make_user('admin', User.Role.ADMIN, is_staff=True, is_superuser=True,
                               first_name='Site', last_name='Admin')
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
        for full_name, position, email, phone in [
                ('Ria Patel', 'Property manager', 'ria@example.com', '021 555 0101'),
                ('Tom Walker', 'Maintenance coordinator', 'tom@example.com', '021 555 0102')]:
            BusinessMember.objects.get_or_create(
                business=business, full_name=full_name,
                defaults={'position': position, 'email': email, 'phone': phone})

        # --- sample listings for the demo provider
        for name, price in [('Regular House Clean', 45), ('End of Tenancy Clean', 280),
                            ('Window Cleaning', 120), ('Carpet Cleaning', 140),
                            ('Gutter Cleaning', 150), ('House Washing', 220)]:
            ServiceProviderService.objects.get_or_create(
                provider=profile, service=Service.objects.get(name=name),
                defaults={'price': price, 'experience_years': 6,
                          'availability': 'Monday to Saturday, 8am to 5pm',
                          'description': f'{name} by Sparkle Home Care. Eco-friendly products included.'})


        # --- more demo providers in other NZ cities, so searches by city show results
        more = [
            ('demo_wellington', 'Harbour Plumbing Co.', 'Wellington', 'Wellington City, Hutt Valley',
             [('Plumbing', 90), ('Electrical Work', 105), ('Gasfitting', 120), ('Drainage & Drain Unblocking', 130)]),
            ('demo_christchurch', 'Canterbury Home Services', 'Christchurch', 'Christchurch and Selwyn',
             [('Painting', 55), ('Heat Pump Install & Service', 170), ('Insulation & Ventilation', 190), ('Handyman', 70)]),
            ('demo_hamilton', 'Waikato Garden & Property', 'Hamilton', 'Hamilton and Cambridge',
             [('Lawn Mowing & Gardens', 55), ('Tree Felling & Removal', 190), ('Section Clearing', 120), ('Fencing & Decking', 90)]),
            ('demo_tauranga', 'Bay Mobile Care', 'Tauranga', 'Tauranga and Mount Maunganui',
             [('Mobile Mechanic', 105), ('Car Detailing', 115), ('Dog Walking', 30), ('Cat Sitting', 25), ('Aquarium Maintenance', 60), ('Mobile Dog Grooming', 85)]),
            ('demo_dunedin', 'Otago Cleaners & Movers', 'Dunedin', 'Dunedin and Mosgiel',
             [('Regular House Clean', 48), ('Carpet Cleaning', 135), ('Furniture Removals', 125), ('Man with a Van', 85)]),
            ('demo_queenstown', 'Southern Lakes Wellbeing & Events', 'Queenstown', 'Queenstown and Wanaka',
             [('Personal Training', 75), ('Mobile Massage', 105), ('Photographer', 260), ('DJ & Sound', 290)]),
            ('demo_rotorua', 'Rotorua Business Hub', 'Rotorua', 'Rotorua and Taupo',
             [('Bookkeeping & GST Returns', 70), ('Website Help for Small Business', 140), ('Computer & Wi-Fi Support', 75), ('Virtual Assistant', 45)]),
        ]
        for username, biz_name, city, area, offers in more:
            user = self.make_user(username, User.Role.SERVICE_PROVIDER,
                                  first_name=biz_name.split()[0], last_name='Provider')
            prof, _ = ProviderProfile.objects.get_or_create(
                user=user,
                defaults={'provider_name': biz_name, 'city': city, 'service_area': area,
                          'experience_years': 5, 'bio': f'Trusted local team in {city}.',
                          'verification_status': ProviderProfile.VerificationStatus.VERIFIED})
            for name, price in offers:
                ServiceProviderService.objects.get_or_create(
                    provider=prof, service=Service.objects.get(name=name),
                    defaults={'price': price, 'experience_years': 5,
                              'availability': 'Monday to Saturday, 8am to 5pm',
                              'description': f'{name} by {biz_name}. Friendly, reliable and fully insured.'})


        # --- make every category available somewhere: each provider offers all services in their specialities
        specialities = {
            'demo_provider': (profile, ['Cleaning', 'Personal'], 1.0),
        }
        extra_specs = {
            'demo_wellington': (['Home Maintenance'], 1.05),
            'demo_christchurch': (['Energy & Healthy Homes', 'Building & Construction'], 1.0),
            'demo_hamilton': (['Outdoor & Rural', 'Family & Care'], 0.95),
            'demo_tauranga': (['Vehicle Services', 'Pets'], 1.0),
            'demo_dunedin': (['Moving & Delivery', 'Education'], 0.95),
            'demo_queenstown': (['Health & Wellbeing', 'Events & Creative'], 1.1),
            'demo_rotorua': (['Business & Finance', 'Technical'], 0.95),
        }
        for username, (cats, factor) in extra_specs.items():
            specialities[username] = (ProviderProfile.objects.get(user__username=username), cats, factor)
        for username, (prof, cats, factor) in specialities.items():
            for service in Service.objects.filter(category__name__in=cats):
                ServiceProviderService.objects.get_or_create(
                    provider=prof, service=service,
                    defaults={'price': round(float(service.base_price) * factor),
                              'experience_years': prof.experience_years or 5,
                              'availability': 'Monday to Saturday, 8am to 5pm',
                              'description': f'{service.name} by {prof.provider_name}. Friendly, reliable and fully insured.'})

        self.stdout.write(self.style.SUCCESS('Demo data is ready.'))
        self.stdout.write(f'Password for every demo account: {DEMO_PASSWORD}')
        self.stdout.write('Usernames: admin, demo_customer, demo_provider, demo_business '
                          '(plus demo_wellington, demo_christchurch, demo_hamilton, demo_tauranga, demo_dunedin, demo_queenstown, demo_rotorua)')
