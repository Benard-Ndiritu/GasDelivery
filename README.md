# GasDelivery API

Django REST + Channels backend for a cooking-gas delivery service: customers order
refills/exchanges, the nearest approved dealer in range receives the order in real time,
and payment is via M-Pesa STK push or cash on delivery.

## Apps

| App | Responsibility |
|---|---|
| `users` | Phone-number accounts (CUSTOMER / DEALER / ADMIN), JWT auth, password reset by email OTP |
| `dealers` | Dealer applications, admin approval, dealer profile |
| `gas` | Gas types (admin) and each dealer's inventory and prices |
| `orders` | Placing orders, dealer matching by distance, status workflow, admin stats |
| `payments` | M-Pesa STK push and callback, cash confirmation |
| `realtime` | WebSocket push of new orders to dealers |

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then edit; set DEBUG=True for local dev
set -a; source .env; set +a
python manage.py migrate
python manage.py runserver      # daphne-backed, so WebSockets work too
```

With `DEBUG=True` and no `DATABASE_URL`/`REDIS_URL`, SQLite and in-memory channel/cache
backends are used.

Run the tests:

```bash
DEBUG=True python manage.py test
```

## Deploying to Render

* **Build command:** `./build.sh` (installs, collects static files, migrates, creates the admin)
* **Start command:** `daphne -b 0.0.0.0 -p $PORT GasDelivery.asgi:application`
* **Health check path:** `/healthz/`
* Python version comes from `.python-version`.
* Add a Render PostgreSQL database (`DATABASE_URL`) and a Render Key Value/Redis instance
  (`REDIS_URL`).
* Set the environment variables listed in [.env.example](.env.example). `SECRET_KEY`
  and `DATABASE_URL` are required; the app refuses to start without them when `DEBUG` is off.

## API overview

All endpoints are under `/api/` and use `Authorization: Bearer <access>` unless marked public.
Errors always include an `"error"` string (plus field-level details for validation errors).

**Users** `/api/users/`
- `POST register/` (public): `phone_number`, `password`, optional `email`. Always creates a CUSTOMER.
- `POST login/` (public): returns `access`, `refresh`, `role`, `phone_number`, `dealer_id`.
- `POST token/refresh/` (public): `{refresh}` → new `access` + rotated `refresh`.
- `POST logout/` (public): `{refresh}` blacklists the refresh token.
- `GET me/`
- `POST request-otp/`, `verify-otp/`, `reset-password/` (public): email OTP reset.
- `GET list/?role=` (admin).

**Dealers** `/api/dealers/`
- `POST apply/` (public): `phone_number`, `password`, `name`, `shop_name`, optional `email`,
  `latitude`, `longitude`, `delivery_radius` (5/7/10).
- `GET application/status/` (dealer): own profile + status.
- `GET|PATCH update/` (approved dealer): edit own profile/location.
- `GET /`, `GET <id>/`: approved dealers.
- `GET applications/?status=` (admin), `POST applications/<id>/action/` (admin):
  `{"action": "approve" | "reject" | "activate" | "deactivate"}`.

**Gas** `/api/gas/`
- `GET types/`; `POST types/`, `GET|PUT|PATCH|DELETE types/<id>/` (admin).
- `GET|POST inventory/`, `GET|PATCH|DELETE inventory/<id>/` (approved dealer).
- `GET dealer/<dealer_id>/inventory/`.

**Orders** `/api/orders/`
- `POST place/` (customer): `gas_type_id`, `order_type` (refill/exchange), `latitude`, `longitude`.
- `GET my/` (customer), `GET dealer/?status=` (dealer), `GET <id>/`.
- `PUT <id>/status/` (dealer): pending → accepted/cancelled → delivering → completed.
- `PUT <id>/cancel/` (customer, pending and unpaid only).
- `GET all/?status=`, `GET stats/` (admin).

**Payments** `/api/payments/`
- `POST mpesa-stk/` (customer): `order_id`, optional `phone_number`. Sends the STK prompt.
- `POST initiate/` (customer): `order_id`, `method` (MPESA/CASH).
- `GET status/<order_id>/`: checks Daraja directly if the callback hasn't arrived.
- `POST cash-confirm/<order_id>/` (dealer): records cash and completes the order.
- `POST mpesa-callback/[<token>/]`: Safaricom only.
- `GET all/?status=` (admin).

**WebSocket**: `wss://<host>/ws/orders/<dealer_id>/?token=<access>` (that dealer or an admin).
Messages: `{"type": "new_order", "order_id", "customer_phone", "gas_type", "order_type", "price"}`.
