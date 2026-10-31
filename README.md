# Servana: Multi-Service Marketplace (New Zealand)

Servana is a Django web application where customers find trusted local service
providers across New Zealand, compare prices, request quotes, book, pay (demo) and
leave reviews. A built-in assistant called **Nova** helps people find a service, and
customers can ask for a live support agent.

> Final project for the Django course. Built with Django, SQLite, HTML, CSS and Bootstrap 5.

- **GitHub:** https://github.com/jenidunston-creator/MultiServiceMarketplace
- **Live site:** https://jenniferdunston.pythonanywhere.com

---

## 1. Features

| Area | What it does |
|---|---|
| **Authentication** | Sign up, log in and log out. Each user picks a role when signing up. |
| **Role-based access** | Four roles (see below). Pages are locked by role. Anyone who is not allowed gets a 403 page. |
| **Services (full CRUD)** | Providers **create, view, edit and delete** their service listings. Customers can search, filter by category and city, and compare up to 3 providers. |
| **Bookings** | Book a service, pay (demo), cancel, and leave a review once the job is completed. Providers update the job status. |
| **Quotations** | Customers request a quote. The provider replies with a price. The customer accepts (this creates a booking) or declines. |
| **Reports / dashboards** | One dashboard for each role. The admin dashboard has live totals, bar charts, and a CSV download of all bookings. |
| **Admin tools** | Activate or deactivate users, verify providers, hide or approve reviews, approve payments, answer complaints, and answer live support chats. |
| **AI assistant (Nova)** | Understands the service, city, date and urgency in a message and shows matching providers. Hands over to a human agent on request. |
| **Payment approval** | Card and bank payments wait for an admin to approve or reject them. Customers and providers are told the result. |
| **Complaints** | Customers and providers can report a problem about a booking. An admin replies and marks it resolved or dismissed. |
| **Responsive design** | Bootstrap 5 and custom CSS. Works on desktop and mobile. |

## 2. User roles

| Role | Can do |
|---|---|
| **Admin** | Everything an admin needs: manage users, verify providers, moderate reviews, approve or reject payments, answer complaints, see all bookings and quotes, answer support chats, export reports, use the Django admin site. |
| **Service Provider** (Staff/Manager role) | A person or a company that offers services. Can add, edit and delete own services, edit own profile, send quotes, update job statuses, report a problem. |
| **Customer** (User role) | An individual who needs a service. Can browse and compare services, book, request quotes, pay, review, report a problem, chat with Nova. |
| **Business** | A company that needs services from providers. Can book services, ask for quotes, pay, review and report problems, with a dashboard that shows its bookings and spending. |

## 3. Technology

- Python 3.12 or newer
- Django 6.0
- SQLite (default Django database)
- Pillow (for image uploads)
- Bootstrap 5.3 (loaded from a CDN)

## 4. Project structure

```
MultiServiceMarketplace/          <- project folder (has manage.py)
├── manage.py
├── requirements.txt
├── README.md
├── MultiServiceMarketplace/      <- settings.py, urls.py, wsgi.py, asgi.py
├── accounts/                     <- users, roles, signup/login, dashboards, provider profile
├── services/                     <- categories, services, provider listings (CRUD)
├── bookings/                     <- bookings, quotations, payments, reviews
├── communication/                <- Nova chat, live support, notifications model
├── templates/                    <- base.html, home.html and one folder per app
└── static/css/style.css
```

## 5. Setup (Windows)

1. **Install Python 3.12 or newer** from python.org. Tick "Add Python to PATH".
2. **Open a terminal** in the project folder (the one that contains `manage.py`).
3. **Create and start a virtual environment:**
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
4. **Install the requirements:**
   ```
   pip install -r requirements.txt
   ```
5. **Create the database tables:**
   ```
   python manage.py migrate
   ```
6. **Add the demo accounts and sample data:**
   ```
   python manage.py seed_demo
   ```
7. **Start the server:**
   ```
   python manage.py runserver
   ```
8. Open **http://127.0.0.1:8000/** in your browser.

On Mac or Linux, use `source venv/bin/activate` in step 3.

## 6. Login details (demo accounts)

These accounts are made by `python manage.py seed_demo`. **They are for demonstration only.**
The password below is public, so it is only used for the customer, provider and business demo accounts.
**The admin account is never given a public password.** On your own computer `seed_demo` makes an `admin`
account (only while `DEBUG` is on). On the live site make your own admin with
`python manage.py createsuperuser` and keep that password private.

| Role | Username | Password | Where it goes after login |
|---|---|---|---|
| Provider | `demo_provider` | `Demo@12345` | `/dashboard/provider/` |
| Customer | `demo_customer` | `Demo@12345` | `/dashboard/customer/` |
| Business | `demo_business` | `Demo@12345` | `/dashboard/business/` |

To make your own admin account instead, run `python manage.py createsuperuser`.
In the Django admin, set the user's **role** to *Admin* so the Servana admin dashboard opens.

## 7. Useful commands

| Command | Purpose |
|---|---|
| `python manage.py runserver` | Start the site |
| `python manage.py migrate` | Create or update the database tables |
| `python manage.py makemigrations` | Make a migration after changing a model |
| `python manage.py seed_demo` | Add demo users, categories, services and listings |
| `python manage.py createsuperuser` | Create another admin user |
| `python manage.py security_check` | Plain-English safety check (admin passwords, DEBUG, Stripe mode, expired IDs). Run it on your computer and on the live site |
| `python manage.py check` | Check the project for problems |

## 8. Main pages

| URL | Page | Who |
|---|---|---|
| `/` | Home | Everyone |
| `/accounts/signup/`, `/accounts/login/` | Sign up, log in | Everyone |
| `/services/` | Search and filter services | Everyone |
| `/services/compare/` | Compare providers | Everyone |
| `/services/new/`, `/services/<id>/edit/`, `/services/<id>/delete/` | Add, edit, delete a service | Provider (own), Admin |
| `/accounts/profile/` | Provider profile | Provider |
| `/bookings/new/?service=<id>` | Book a service | Customer, Business |
| `/bookings/` | Bookings (customer) or jobs (provider) | Logged-in users |
| `/quotations/` | Quotes and quote requests | Logged-in users |
| `/bookings/<id>/pay/` | Pay for a booking (demo, then admin approval) | Customer, Business |
| `/bookings/payments/` | Approve or reject payments | Admin |
| `/bookings/<id>/complaint/` | Report a problem about a booking | Customer, Business, Provider |
| `/bookings/complaints/` | Your complaints (admin: all complaints and replies) | Logged-in users |
| `/communication/` | Chat with Nova | Logged-in users |
| `/communication/inbox/` | Live support inbox | Admin |
| `/dashboard/` | Sends you to the dashboard for your role | Logged-in users |
| `/admin/` | Django admin site | Admin |

## 9. Database

Main models and how they are related (all by foreign keys or one-to-one links):

- `User` (custom, with a `role`) has one `CustomerProfile` or `ProviderProfile`, or owns a `Business`.
- `ServiceCategory` has many `Service`. A provider offers a service through `ServiceProviderService`.
- A `ServiceRequest` (made by a customer) leads to a `Quotation` and a `Booking`.
- A `Booking` has one `Payment` (approved by an admin), one `Review`, and can have many `Complaint` records (raised by the customer or the provider).
- `ChatConversation` has many `ChatMessage`. `Notification` belongs to a user.

All models are registered in the Django admin.

## 10. Security and anti-scam protection

- Passwords are hashed by Django. CSRF protection is on for every form.
- `login_required` and a `role_required` decorator protect every private page. Admin-only pages return **403 Forbidden** to other roles.
- Users can only see or change their own bookings, listings and chats. Actions that change data accept **POST** only.
- **Verified accounts only.** A new user must confirm their email, confirm their mobile number with a 6-digit code, and send passport (and NZ visa if not a NZ passport) details that an **admin approves**. Until then they cannot book, pay, chat or offer services, and their listings are hidden from customers.
- Passport numbers are stored only as a one-way hash (one passport can be used on one account only). Passport and visa photos are stored in a private folder, never in public media, and only the owner and admins can open them. Expired passports and visas are rejected, and an account that was approved is blocked again (and its listings hidden) the day its passport or visa runs out, until new documents are sent and approved. Uploaded ID files must really be a JPG, PNG or PDF.
- **Protected payments (escrow).** Customers pay Servana through Stripe Checkout (NZD, test mode only). The provider cannot start work until the payment is held. After the work is completed and the customer confirms it, the admin releases the money to the provider. The admin can refund a held payment.
- Customers can choose to pay in full or pay a 30% advance and the balance later.
- Payment amounts are decided by the server, never the browser. Every payment is confirmed by asking Stripe directly (status, NZD amount and booking), repeated confirmations are ignored, and live keys are refused.
- Login attempts are limited (5 wrong tries locks a username for 15 minutes). Sign-ups are rate limited, email addresses must be unique, and a hidden field catches spam robots.
- Messages, reviews, quotes and descriptions cannot contain links, emails, phone numbers or off-site payment talk (bank transfer, WhatsApp, crypto, gift cards).
- Complaints go to the admin. Reviews can be hidden by the admin.

## 11. Notes and limitations

- **Stripe runs in TEST mode.** No real money moves. Stripe supports New Zealand and NZD. Set `STRIPE_SECRET_KEY` (a test key starting `sk_test_`) as an environment variable. A real launch would use Stripe Connect to pay providers out.
- **Email and SMS are not connected.** In demo mode the verification link and code are shown on the page (`DEMO_SHOW_CODES`). A real site would use an SMS service such as Twilio and a real email account.
- **Passport and visa checks are done by a person (the admin).** There is no free official service that confirms a passport or visa online.
- **Nova is a rule-based assistant** (keywords and database lookups). It does not use an outside AI service.
- A provider is one account, even when it is a company with employees.
- The project uses the default SQLite database, which is fine for a course project.

## 12. Deployment

Step-by-step instructions for GitHub and PythonAnywhere are in **[DEPLOY.md](DEPLOY.md)**.
On the live site the secret key and host name come from environment variables
(`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`), so nothing secret is stored in GitHub.
Without those variables the project runs in local development mode.

## 13. Course requirement checklist

| Requirement | Where it is done |
|---|---|
| Signup, login, logout | `accounts/` |
| At least 3 roles (Admin, Staff, User) | Admin, Provider, Customer (plus Business) |
| 3 core modules: users, main module, reports | Accounts and dashboards, Bookings and quotes, Admin reports |
| Full CRUD in one module | Services (`/services/`) |
| Database with migrations and foreign keys | SQLite, migrations in each app |
| HTML, CSS, Bootstrap, responsive | `templates/`, `static/css/style.css`, Bootstrap 5 |
| Login required and role-based access | `accounts/decorators.py` and every view |
| Admin-only pages restricted | Admin dashboard, payment approvals, support inbox and admin actions |
| Models registered in the Django admin | `admin.py` in every app |
| Search | Service search by keyword, category and city |
| Dashboard charts | Bar charts on the admin dashboard |
| File uploads | Service photos and provider photos |
| README, requirements.txt, admin login | This file, `requirements.txt`, section 6 |
