"""UI surface — owned by the UI team.

UI_VARIANT=v2 simulates a component refactor: the sign-in label changes and the
order list loses its test-id. Use it to demo self-healing live.
"""

import os

from fastapi import APIRouter, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse

from app.domain import tenant_of

UI_VARIANT = os.getenv("UI_VARIANT", "v1")
SIGN_IN_LABEL = "Sign in" if UI_VARIANT == "v1" else "Log in"
LIST_CLASS = "order-list" if UI_VARIANT == "v1" else "orders-table"
LIST_TESTID = ' data-testid="order-list"' if UI_VARIANT == "v1" else ""
# v2 also drops the login button's test-id — the usual casualty of a refactor.
SUBMIT_TESTID = ' data-testid="login-submit"' if UI_VARIANT == "v1" else ""

router = APIRouter()

SHELL = """<!doctype html><html><head><meta charset="utf-8">
<title>Shop Back Office</title><style>
body{{font-family:system-ui,sans-serif;margin:2rem;max-width:46rem}}
li{{border:1px solid #ccc;padding:.6rem;margin:.4rem 0;list-style:none}}
input,button{{padding:.5rem;font-size:1rem}}
</style></head><body>{body}</body></html>"""


@router.get("/", response_class=RedirectResponse)
def root():
    return RedirectResponse("/login")


@router.get("/login", response_class=HTMLResponse)
def login_page():
    return SHELL.format(body=f"""
      <h1>Shop Back Office</h1>
      <label for="email">Email</label>
      <input id="email" data-testid="email" type="email">
      <label for="password">Password</label>
      <input id="password" data-testid="password" type="password">
      <button id="submit"{SUBMIT_TESTID} onclick="doLogin()">{SIGN_IN_LABEL}</button>
      <p data-testid="login-error" style="color:#b00"></p>
      <script>
      async function doLogin() {{
        const r = await fetch('/api/auth/login', {{
          method:'POST', headers:{{'Content-Type':'application/json'}},
          body: JSON.stringify({{email:email.value, password:password.value}})
        }});
        if (r.ok) location.href = '/orders';
        else document.querySelector('[data-testid=login-error]').textContent = 'Invalid credentials';
      }}
      </script>""")


@router.get("/orders", response_class=HTMLResponse)
def orders_page(tenant: str | None = Cookie(default=None),
                session: str | None = Cookie(default=None)):
    if not session:
        return RedirectResponse("/login")
    t = tenant_of(None, tenant)
    items = "".join(
        f'<li data-testid="order-item">'
        f'<strong data-testid="order-customer">{o.customer}</strong> '
        f'<span data-testid="order-total">${o.total:.2f}</span> — shipping '
        f'<span data-testid="order-shipping">{"free" if o.shipping == 0 else f"${o.shipping:.2f}"}</span> '
        f'<span data-testid="order-status">{"shipped" if o.shipped else "pending"}</span> '
        f'<button data-testid="ship-button" onclick="ship({i}+1)">Ship</button>'
        f'</li>'
        for i, o in enumerate(t.orders)
    ) or '<li data-testid="empty-state">No orders yet.</li>'
    return SHELL.format(body=f"""
      <h1 data-testid="orders-heading">Orders</h1>
      <ul class="{LIST_CLASS}"{LIST_TESTID}>{items}</ul>
      <script>
      async function ship(i) {{
        await fetch('/api/orders/' + i + '/ship', {{method:'POST'}});
        location.reload();
      }}
      </script>""")
