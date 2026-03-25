from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException

from .pncp_client import PNCPClientError
from .schemas import HealthResponse, MarketSearchRequest, MarketSearchResponse
from .service import market_search

router = APIRouter(prefix="/pncp-research", tags=["pncp-research"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(ok=True)


@router.post("/market-search", response_model=MarketSearchResponse)
async def market_search_endpoint(body: MarketSearchRequest) -> MarketSearchResponse:
    try:
        data = await market_search(body)
        return MarketSearchResponse(**data)
    except PNCPClientError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def create_app() -> FastAPI:
    app = FastAPI(title="PNCP Researcher Service", version="1.0.0")
    app.include_router(router, prefix="/api")
    return app
