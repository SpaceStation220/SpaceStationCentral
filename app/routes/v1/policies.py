from typing import cast

from fastapi import APIRouter, Request, status
from sqlmodel import select
from sqlmodel.sql.expression import Select

from app.database.models import BenefitPolicy, BenefitsScope
from app.deps import SessionDep
from app.schemas.v1.generic import PaginatedResponse, paginate_selection


policies_router = APIRouter(prefix="/policies", tags=["Policies"])


@policies_router.get("/benefits/scopes", status_code=status.HTTP_200_OK)
async def get_benefit_scopes(
    session: SessionDep,
    request: Request,
    active_only: bool = True,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[BenefitsScope]:
    selection = cast(Select[tuple[BenefitsScope]], select(BenefitsScope))  # pyright: ignore[reportInvalidCast]
    if active_only:
        selection = selection.where(BenefitsScope.active)
    return paginate_selection(session, selection, request, page, page_size)


@policies_router.get("/benefits", status_code=status.HTTP_200_OK)
async def get_benefit_policies(
    session: SessionDep,
    request: Request,
    cause: str | None = None,
    scope: str | None = None,
    active_only: bool = True,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[BenefitPolicy]:
    selection = cast(Select[tuple[BenefitPolicy]], select(BenefitPolicy))  # pyright: ignore[reportInvalidCast]
    if cause:
        selection = selection.where(BenefitPolicy.cause == cause)
    if scope:
        selection = selection.where(BenefitPolicy.scope == scope)
    if active_only:
        selection = selection.where(BenefitPolicy.active)
    return paginate_selection(session, selection, request, page, page_size)
