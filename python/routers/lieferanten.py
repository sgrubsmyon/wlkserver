from fastapi import APIRouter

router = APIRouter()


@router.get("/lieferanten/", tags=["lieferanten"])
async def read_lieferanten():
    return [{"bezeichnung": "Costa Rica Cola"}, {"bezeichnung": "Rosinen"}]


@router.get("/lieferanten/{lief_id}", tags=["lieferanten"])
async def read_lieferant(artikel_id: str):
    """
    Reads a single Lieferant by lief_id.

    Args:
        lief_id (str): The lief_id of the Lieferant to read.

    Returns:
        dict: A dictionary with the data of the read Lieferant.
    """
    return {"lief_id": lief_id}