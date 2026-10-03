import os
import subprocess
import time
import uuid
from urllib.parse import urlparse

import httpx
import pytest

MANAGER = {"email": "manager@shop.test", "password": "correct-horse"}


@pytest.fixture(scope="session")
def base_url(worker_id) -> str:
    """One app instance per xdist worker, on its own port.

    Sharing a single server across workers means racing to start it and racing
    to tear it down. Giving each worker its own is simpler and, because all
    state is tenant-scoped anyway, costs nothing. Set BASE_URL to point the
    whole suite at an already-running app instead — that is what CI does.

    (Session-scoped on purpose: pytest-playwright ships its own session-scoped
    `base_url` and pytest will not let a function-scoped one shadow it.)
    """
    if url := os.getenv("BASE_URL"):
        return url
    worker = 0 if worker_id == "master" else int(worker_id.removeprefix("gw"))
    # The UI variant is part of the port. Otherwise a v2 server left listening
    # from the previous run gets silently reused by the next v1 run, and you
    # demo the wrong app in front of an audience.
    variant = 0 if os.getenv("UI_VARIANT", "v1") == "v1" else 100
    return f"http://127.0.0.1:{8000 + variant + worker}"


@pytest.fixture(scope="session", autouse=True)
def app_server(base_url):
    """Boot the app under test unless something is already serving it.

    Set AUTOSTART_APP=0 in CI, where the app is started as its own step.
    """
    if os.getenv("AUTOSTART_APP", "1") != "1" or _is_up(base_url):
        yield
        return
    proc = subprocess.Popen(
        ["uvicorn", "app.main:app", "--port", str(urlparse(base_url).port),
         "--log-level", "warning"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(100):
        if _is_up(base_url):
            break
        time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError(f"app under test never came up on {base_url}")
    yield
    proc.terminate()
    proc.wait(timeout=10)


def _is_up(base_url: str) -> bool:
    try:
        httpx.get(f"{base_url}/api/orders", timeout=1)
        return True
    except Exception:
        return False


@pytest.fixture
def tenant() -> str:
    """Every scenario gets its own slice of server state — no reset step, no
    ordering dependency, no way for two scenarios to collide."""
    return f"t-{uuid.uuid4().hex[:10]}"


@pytest.fixture
def context_data() -> dict:
    """Scratch space shared between Given/When/Then inside one scenario."""
    return {}


@pytest.fixture
def api(base_url, tenant):
    """Thin API client. This is what the API-layer binding drives."""
    with httpx.Client(base_url=base_url, headers={"X-Tenant": tenant}, timeout=10) as c:
        yield c


@pytest.fixture
def ui_page(page, tenant, base_url):
    """Playwright's `page`, with this scenario's tenant cookie attached."""
    page.context.add_cookies([{"name": "tenant", "value": tenant, "url": base_url}])
    return page
