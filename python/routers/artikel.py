from fastapi import APIRouter, Depends, HTTPException

# from ..dependencies import get_token_header

router = APIRouter(
    prefix="/artikel",
    tags=["artikel"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


fake_artikel_db = {"cr01": {"bezeichnung": "Costa Rica Cola"}, "ros": {"bezeichnung": "Rosinen"}}


@router.get("/")
async def read_artikel():
    return fake_artikel_db


@router.get("/{artikel_id}")
async def read_single_artikel(artikel_id: str):
    if artikel_id not in fake_artikel_db:
        raise HTTPException(status_code=404, detail="Artikel not found")
    return {"bezeichnung": fake_artikel_db[artikel_id]["bezeichnung"], "artikel_id": artikel_id}


@router.put(
    "/{artikel_id}",
    tags=["artikel"],
    responses={403: {"description": "Operation forbidden"}},
)
async def update_artikel(artikel_id: str):
    if artikel_id != "cr01":
        raise HTTPException(
            status_code=403, detail="You can only update the artikel: cr01"
        )
    return {"artikel_id": artikel_id, "name": "The great Costa Rica Cola"}