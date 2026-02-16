from fastapi import FastAPI
from fastapi.responses import FileResponse

# from .dependencies import get_query_token, get_token_header
# from .internal import admin
from .routers import (
  artikel, lieferant, produktgruppe,
  mwst, pfand, rabattaktion,
  verkauf,
)


# app = FastAPI(dependencies=[Depends(get_query_token)])
app = FastAPI()
favicon_path = 'assets/favicon.gif'

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