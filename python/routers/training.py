"""Training mode endpoints.

`TRAINING_MODE` turns the whole API instance into a sandbox: it runs against
the disposable database configured in `TRAINING_DB_URL` (created and seeded on
startup by `business/training.py`), so sales, settlements *and* master-data
edits never touch production. These endpoints report the mode and reset the
sandbox.
"""
from fastapi import APIRouter, Depends, HTTPException

from ..business.training import reset_training_data
from ..dependencies import require_admin, require_user
from ..session import SessionDep, get_production_engine, is_training_mode

router = APIRouter(
    prefix="/training",
    tags=["training"],
    responses={404: {"description": "Not found"}},
)


@router.get("/status")
def training_status(_user=Depends(require_user)) -> dict:
    return {"training_mode": is_training_mode()}


@router.post("/reset")
def reset_training(session: SessionDep, _user=Depends(require_admin)) -> dict:
    """Clear the sandbox and seed the test catalog again (training mode only)."""
    if not is_training_mode():
        raise HTTPException(status_code=400, detail="Not running in training mode")
    reset_training_data(session, get_production_engine())
    return {"status": "reset"}
