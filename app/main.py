"""Assembles the two surfaces. Deliberately thin.

    uvicorn app.main:app --port 8000
    UI_VARIANT=v2 uvicorn app.main:app --port 8000    # simulate a UI refactor
"""

from fastapi import FastAPI

from app import api, ui

app = FastAPI(title="Shop Back Office")
app.include_router(api.router)
app.include_router(ui.router)
