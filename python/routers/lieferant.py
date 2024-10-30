from dotenv import load_dotenv

from fastapi import APIRouter, Depends, HTTPException, Query

# from ..dependencies import get_token_header

from ..models import Lieferant

load_dotenv()  # take environment variables from .env file


router = APIRouter(
    prefix="/lieferant",
    tags=["lieferant"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)