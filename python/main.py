import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .business.training import ensure_training_database
from .business.vat_calculator import vat_rounding_method
from .dependencies import require_user

# from .dependencies import get_query_token, get_token_header
# from .internal import admin
from .routers import (
  artikel, lieferant, produktgruppe,
  mwst, pfand, rabattaktion,
  verkauf,
  kassenstand, gutschein, anzahlung,
  abrechnung_tag, abrechnung_monat, abrechnung_jahr,
  zaehlprotokoll, bestellung,
  tse,
  auth, users, import_export, training,
)


# app = FastAPI(dependencies=[Depends(get_query_token)])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # In training mode this creates and seeds the disposable sandbox database.
    ensure_training_database()
    yield


app = FastAPI(lifespan=lifespan)
favicon_path = 'assets/favicon.gif'

# Restrict CORS to the configured frontend origins (comma separated, defaults to
# the SvelteKit dev server). Set CORS_ORIGINS in production.
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fail fast at startup on a misconfigured rounding method instead of erroring per request.
vat_rounding_method()

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)

protected_routers = [
    artikel.router, lieferant.router, produktgruppe.router,
    mwst.router, pfand.router, rabattaktion.router,
    verkauf.router, kassenstand.router, gutschein.router, anzahlung.router,
    abrechnung_tag.router, abrechnung_monat.router, abrechnung_jahr.router,
    zaehlprotokoll.router, bestellung.router,
    tse.router, users.router, import_export.router, training.router,
]
for router in protected_routers:
    app.include_router(router, dependencies=[Depends(require_user)])
app.include_router(auth.router)
# app.include_router(
#     admin.router,
#     prefix="/admin",
#     tags=["admin"],
#     dependencies=[Depends(get_token_header)],
#     responses={418: {"description": "I'm a teapot"}},
# )


@app.get("/")
async def root():
    return {"message": "Welcome to the Weltladenkasse API!"}