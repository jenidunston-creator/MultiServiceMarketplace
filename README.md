# Servana: Multi-Service Marketplace (New Zealand)

Servana is a Django web application where customers find trusted local service
providers across New Zealand, compare prices, request quotes, book, pay (demo) and
leave reviews. A built-in assistant called **Nova** helps people find a service, and
customers can ask for a live support agent.

> Final project for the Django course. Built with Django, SQLite, HTML, CSS and Bootstrap 5.

- **GitHub:** `ADD YOUR GITHUB LINK HERE`
- **Live site:** `ADD YOUR DEPLOY LINK HERE`

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
| **Admin tools** | Activate or deactivate users, verify providers, hide or approve reviews, and answer live support chats. |
| **AI assistant (Nova)** | Understands the service, city, date and urgency in a message and shows matching providers. Hands over to a human agent on request. |
| **Responsive design** | Bootstrap 5 and custom CSS. Works on desktop and mobile. |

## 2. User roles

| Role | Can do |
|---|---|
| **Admin** | Everything an admin needs: manage users, verify providers, moderate reviews, see all bookings and quotes, answer support chats, export reports, use the Django admin site. |
| **Service Provider** (Staff/Manager role) | Add, edit and delete own services, edit own profile, send quotes, update job statuses. |
| **Customer** (User role) | Browse and compare services, book, request quotes, pay, review, chat with Nova. |
| **Business** | Like a customer, and can also manage a team of members from the business dashboard. |

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

| Role | Username | Password | Where it goes after login |
|---|---|---|---|
| Admin | `admin` | `Demo@12345` | `/dashboard/admin-panel/` (also `/admin/` for the Django admin site) |
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
| `/communication/` | Chat with Nova | Logged-in users |
| `/communication/inbox/` | Live support inbox | Admin |
| `/dashboard/` | Sends you to the dashboard for your role | Logged-in users |
| `/admin/` | Django admin site | Admin |

## 9. Database

Main models and how they are related (all by foreign keys or one-to-one links):

- `User` (custom, with a `role`) has one `CustomerProfile` or `ProviderProfile`, or owns a `Business`.
- `ServiceCategory` has many `Service`. A provider offers a service through `ServiceProviderService`.
- A `ServiceRequest` (made by a customer) leads to a `Quotation` and a `Booking`.
- A `Booking` has one `Payment` and one `Review`.
- `ChatConversation` has many `ChatMessage`. `Notification` belongs to a user.

All models are registered in the Django admin.

## 10. Security

- Passwords are hashed by Django. CSRF protection is on for every form.
- `login_required` and a `role_required` decorator protect every private page.
- Admin-only pages return **403 Forbidden** to other roles.
- Users can only see or change their own bookings, listings and chats.
- Actions that change data (status, pay, delete, accept) accept **POST** only.

## 11. Notes and limitations

- **Payments are a demo.** The site saves the payment method and status but never takes
  real money and never stores card numbers.
- **Nova is a rule-based assistant** (keywords and database lookups). It does not use an outside AI service.
- The business dashboard manages a team and shows the business's own bookings. Assigning jobs to
  team members is not built.
- The project uses the default SQLite database, which is fine for a course project.
  A busy real website would use PostgreSQL or MySQL instead.

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
| Admin-only pages restricted | Admin dashboard, support inbox and admin actions |
| Models registered in the Django admin | `admin.py` in every app |
| Search | Service search by keyword, category and city |
| Dashboard charts | Bar charts on the admin dashboard |
| File uploads | Service photos and provider photos |
| README, requirements.txt, admin login | This file, `requirements.txt`, section 6 |
