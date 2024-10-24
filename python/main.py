from fastapi import Depends, FastAPI

# from .dependencies import get_query_token, get_token_header
# from .internal import admin
from .routers import artikel, lieferanten

# app = FastAPI(dependencies=[Depends(get_query_token)])
app = FastAPI()


app.include_router(artikel.router)
app.include_router(lieferanten.router)
# app.include_router(
#     admin.router,
#     prefix="/admin",
#     tags=["admin"],
#     dependencies=[Depends(get_token_header)],
#     responses={418: {"description": "I'm a teapot"}},
# )


@app.get("/")
async def root():
    return {"message": "Hello Bigger Applications!"}