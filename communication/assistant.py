"""Nova, the Servana assistant.

Nova is a simple rule-based helper (no outside AI service is needed).
It looks for keywords in what the customer types, remembers the service,
city, date and urgency, and answers using real data from the database.
"""
from urllib.parse import urlencode

from services.models import Service, ServiceProviderService

WELCOME = ("Kia ora! I'm Nova, the Servana assistant. Tell me what you need "
           "(for example: \"I need a plumber in Wellington tomorrow\") and I will help you find a provider.")

# keyword in the message -> text to look for in the service name
# (the order matters: the first match wins)
SERVICE_WORDS = [
    ('tenancy', 'End of Tenancy'), ('wof', 'WOF'),
    ('plumb', 'Plumbing'), ('leak', 'Plumbing'), ('drain', 'Plumbing'), ('tap', 'Plumbing'),
    ('electric', 'Electrical'), ('wiring', 'Electrical'), ('socket', 'Electrical'),
    ('lawn', 'Lawn'), ('garden', 'Lawn'), ('mow', 'Lawn'),
    ('paint', 'Painting'),
    ('mechanic', 'Mechanic'), ("won't start", 'Mechanic'), ('wont start', 'Mechanic'), ('car', 'Mechanic'),
    ('clean', 'Regular House Clean'),
    ('parcel', 'Parcel'), ('deliver', 'Parcel'), ('courier', 'Parcel'),
    ('wifi', 'Wi-Fi'), ('wi-fi', 'Wi-Fi'), ('laptop', 'Computer'), ('computer', 'Computer'), ('internet', 'Computer'),
    ('event', 'Event'), ('party', 'Event'),
]

CITIES = ['Auckland', 'Wellington', 'Christchurch', 'Hamilton', 'Tauranga',
          'Dunedin', 'Queenstown', 'Rotorua', 'Nelson']
# a few suburbs that people type instead of the city
SUBURBS = {'henderson': 'Auckland', 'manukau': 'Auckland', 'takapuna': 'Auckland',
           'newmarket': 'Auckland', 'parnell': 'Auckland', 'north shore': 'Auckland',
           'lower hutt': 'Wellington', 'petone': 'Wellington'}

DATE_WORDS = ['today', 'tonight', 'tomorrow', 'this weekend', 'next week',
              'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
URGENT_WORDS = ['urgent', 'emergency', 'asap', 'right now', 'immediately']


def update_extracted(data, text):
    """Read the message and add anything new to what Nova already knows."""
    data = dict(data or {})
    lower = text.lower()

    for keyword, search in SERVICE_WORDS:
        if keyword in lower:
            service = Service.objects.filter(is_active=True, name__icontains=search).first()
            if service:
                data['service'] = service.name
                data['category'] = service.category.name
                data['problem'] = text[:120]
                break

    for suburb, city in SUBURBS.items():
        if suburb in lower:
            data['city'] = city
            data['area'] = suburb.title()
    for city in CITIES:
        if city.lower() in lower:
            data['city'] = city

    for word in DATE_WORDS:
        if word in lower:
            data['date'] = word.title()
            break

    if any(word in lower for word in URGENT_WORDS):
        data['urgency'] = 'Urgent'
    return data


def match_link(data):
    """Link to the services page, already filtered."""
    if not data.get('service'):
        return ''
    params = {'q': data['service']}
    if data.get('city'):
        params['location'] = data['city']
    return '/services/?' + urlencode(params)


def count_matches(data):
    listings = ServiceProviderService.objects.filter(
        is_active=True, service__name=data['service'])
    if data.get('city'):
        listings = listings.filter(provider__city__iexact=data['city'])
    return listings.count()


def has_any(text, words):
    return any(word in text for word in words)


def nova_reply(text, data, changed=True):
    """Return Nova's answer to one message.

    changed is True when this message taught Nova something new.
    """
    lower = text.lower()

    # questions about how the website works
    if has_any(lower, ['pay', 'payment', 'card', 'refund']):
        return ("You can pay from the My Bookings page: press Pay, choose a method and confirm. "
                "Payments in this project are a demo, so no real money is taken.")
    if has_any(lower, ['cancel']):
        return "You can cancel a booking from My Bookings while it is Pending or Confirmed. Press Cancel next to it."
    if has_any(lower, ['review', 'rating', 'feedback']):
        return "After a provider marks your job as Completed, a Leave review button appears on the My Bookings page."
    if has_any(lower, ['quote', 'quotation', 'price', 'cost', 'how much']) and not data.get('service'):
        return ("Open any service and press Request a quote. The provider replies with a price, "
                "and you can accept it from the Quotations page.")
    if has_any(lower, ['human', 'agent', 'person', 'support', 'complaint']):
        return "Press the Connect to live agent button above and someone from our team will join this chat."
    if lower.strip() in ('hi', 'hello', 'hey', 'kia ora', 'hi nova', 'hello nova'):
        return "Kia ora! What service can I help you find today?"
    if has_any(lower, ['thank', 'cheers']):
        return "You're welcome! Is there anything else I can help with?"

    # finding a service
    if data.get('service') and changed:
        if not data.get('city'):
            return (f"Thanks! I noted {data['service']}. Which city are you in, "
                    "so I can look for providers near you?")
        count = count_matches(data)
        urgent = " I have marked this as urgent." if data.get('urgency') else ""
        if count:
            return (f"Good news! {count} provider{'s' if count != 1 else ''} "
                    f"{'offers' if count == 1 else 'offer'} "
                    f"{data['service']} in {data['city']}.{urgent} Press Show matching providers on the "
                    "right to compare them, then book or ask for a quote.")
        elsewhere = ServiceProviderService.objects.filter(
            is_active=True, service__name=data['service']).count()
        if elsewhere:
            return (f"No provider offers {data['service']} in {data['city']} yet, but {elsewhere} "
                    f"offer{'s' if elsewhere == 1 else ''} it in other areas.{urgent} Press Show matching "
                    "providers to see them, or ask for a live agent.")
        return (f"I could not find any provider for {data['service']} yet.{urgent} "
                "You can ask for a live agent and our team will help.")

    if data.get('service'):
        return ("I'm not sure I understood that. I still have your request for "
                f"{data['service']}. Press Show matching providers on the right, or tell me more "
                "(city, date, how urgent it is).")

    return ("I'm not sure I understood. Try telling me the service and the city, for example "
            "\"cleaner in Hamilton on Friday\". I can also help with payments, bookings, quotes and reviews.")
