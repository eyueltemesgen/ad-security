# AD Security Camera Solution

A complete production-ready web application for a security camera solution company
(equipment sales plus installation, maintenance, networking, access control, time
attendance, video intercom, and IT/web solutions). It includes three surfaces:

1. **Public marketing website** — home, products, services, gallery, FAQ, contact.
2. **Customer portal** — cart, checkout, orders, service requests (with file upload),
   order tracking, profile, notifications.
3. **Admin control system** — dashboard & analytics, customers, orders, service
   requests, messages, products, categories, services, gallery, testimonials,
   FAQs, media library, and a full CMS (pages, homepage, navigation, settings,
   social links, SEO, appearance) plus audit logs.

## Tech stack

- Python 3 / Flask
- Flask-SQLAlchemy (SQLite by default; swap via `DATABASE_URL` for Postgres/MySQL)
- Flask-Login for customer sessions; a separate signed admin session
- Jinja2 server-rendered templates with a responsive security-themed design
- No external JS framework required

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export FLASK_APP=run.py
flask init-db      # create tables
flask seed         # demo content, admin + customer accounts
flask run          # http://127.0.0.1:5000
```

Seeded accounts:

| Role        | Email                        | Password      |
|-------------|------------------------------|---------------|
| Admin       | admin@adsecurity.example     | Admin@12345   |
| Customer    | customer@example.com         | Customer@123  |

## Configuration

All secrets and environment values come from environment variables (see
`.env.example`). Key settings:

- `SECRET_KEY` — session signing key
- `DATABASE_URL` — SQLAlchemy connection string
- `MAIL_*` — SMTP for password reset (falls back to an on-screen token link)
- `PORT` — used by the dev `run.py`

## Project layout

```
ad-security/
  app/
    __init__.py     # app factory, context processors, error handlers
    config.py       # configuration
    extensions.py   # db + login_manager
    models.py       # all models
    main.py         # public website blueprint
    auth.py         # register/login/password blueprint
    customer.py     # portal: cart/checkout/orders/service requests
    admin.py        # admin control system blueprint
    seed.py         # demo data
    utils.py        # settings, uploads, notifications, audit helpers
    templates/      # public/, auth/, customer/, admin/, errors/, partials/
    static/
  run.py / wsgi.py  # dev / production entry points
  requirements.txt
  .env.example
```

## Deployment

For gunicorn: `gunicorn wsgi:app -b 0.0.0.0:8000`. Ensure uploaded media is
persisted (the `app/static/img/uploads` folder) and `SECRET_KEY` is set.

## Testing

Run the acceptance smoke checks (scripts under your CI) that initialize the DB,
seed, and exercise every route for guest, customer, and admin sessions.