import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .business.vat_calculator import vat_rounding_method

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
app = FastAPI()
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

app.include_router(artikel.router)
app.include_router(lieferant.router)
app.include_router(produktgruppe.router)
app.include_router(mwst.router)
app.include_router(pfand.router)
app.include_router(rabattaktion.router)
app.include_router(verkauf.router)
app.include_router(kassenstand.router)
app.include_router(gutschein.router)
app.include_router(anzahlung.router)
app.include_router(abrechnung_tag.router)
app.include_router(abrechnung_monat.router)
app.include_router(abrechnung_jahr.router)
app.include_router(zaehlprotokoll.router)
app.include_router(bestellung.router)
app.include_router(tse.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(import_export.router)
app.include_router(training.router)
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