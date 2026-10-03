"""API surface — owned by the API team."""

from fastapi import APIRouter, Cookie, Header, HTTPException, Response
from pydantic import BaseModel

from app.domain import PASSWORD, place_order, tenant_of

router = APIRouter()


class LoginBody(BaseModel):
    email: str
    password: str


class OrderBody(BaseModel):
    customer: str
    total: float


@router.post("/api/auth/login")
def login(body: LoginBody, response: Response,
          x_tenant: str | None = Header(default=None),
          tenant: str | None = Cookie(default=None)):
    t = tenant_of(x_tenant, tenant)
    if body.password != PASSWORD:
        raise HTTPException(401, "invalid credentials")
    token = f"tok-{body.email}"
    t.sessions[token] = body.email
    response.set_cookie("session", token)
    return {"token": token, "email": body.email, "role": "manager"}


@router.post("/api/orders", status_code=201)
def create_order(body: OrderBody,
                 x_tenant: str | None = Header(default=None),
                 tenant: str | None = Cookie(default=None)):
    t = tenant_of(x_tenant, tenant)
    return place_order(t, body.customer, body.total).__dict__


@router.post("/api/orders/{index}/ship")
def ship(index: int,
         x_tenant: str | None = Header(default=None),
         tenant: str | None = Cookie(default=None)):
    t = tenant_of(x_tenant, tenant)
    if index >= len(t.orders):
        raise HTTPException(404, "no such order")
    t.orders[index].shipped = True
    return {"shipped": True, "customer": t.orders[index].customer}


@router.get("/api/orders")
def orders(x_tenant: str | None = Header(default=None),
           tenant: str | None = Cookie(default=None),
           session: str | None = Cookie(default=None)):
    t = tenant_of(x_tenant, tenant)
    if session is not None and session not in t.sessions:
        raise HTTPException(401, "not authenticated")
    return {"orders": [o.__dict__ for o in t.orders]}
