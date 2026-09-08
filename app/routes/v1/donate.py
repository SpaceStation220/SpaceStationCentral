import logging
from datetime import timedelta
from typing import TypeVar, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import select
from sqlmodel.sql.expression import Select

from app.core.utils import utcnow2
from app.database.models import BenefitGrant, BenefitPolicy, BenefitsScope, Player
from app.deps import SessionDep, verify_bearer
from app.routes.v1.player import get_or_create_player_by_discord_id
from app.schemas.v1.donate import DonationPatch, DonationResponse, NewDonationDiscord
from app.schemas.v1.generic import PaginatedResponse, paginate_selection


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/donates", tags=["Donate"])

T = TypeVar("T")


def grant_response(grant: BenefitGrant) -> DonationResponse:
    return DonationResponse.model_validate(grant, from_attributes=True)


def filter_donations(
    selection: Select[tuple[T, ...]],
    ckey: str | None = None,
    discord_id: str | None = None,
    cause: str | None = None,
    scope: str | None = None,
    active_only: bool = True,
) -> Select[tuple[T, ...]]:
    if ckey:
        selection = selection.where(Player.ckey == ckey)
    if discord_id:
        selection = selection.where(Player.discord_id == discord_id)
    if cause:
        selection = selection.where(BenefitGrant.cause == cause)
    if scope:
        selection = selection.where(BenefitGrant.scope == scope)
    if active_only:
        selection = selection.where(BenefitGrant.valid).where(BenefitGrant.expiration_time > utcnow2())
    return selection


async def resolve_benefit_source(
    session: SessionDep, cause: str | None, scope: str
) -> int | None:
    if cause is None:
        return None

    policy = session.exec(
        select(BenefitPolicy).where(
            BenefitPolicy.cause == cause,
            BenefitPolicy.scope == scope,
        )
    ).first()
    if policy is None:
        policy = session.exec(
            select(BenefitPolicy).where(
                BenefitPolicy.cause == cause,
                BenefitPolicy.scope == "*",
            )
        ).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benefit policy not found")
    if policy.active is False:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Benefit policy is not active")
    return policy.benefit_tier


@router.get("", status_code=status.HTTP_200_OK)
async def get_donations(
    session: SessionDep,
    request: Request,
    ckey: str | None = None,
    discord_id: str | None = None,
    cause: str | None = None,
    scope: str | None = None,
    active_only: bool = True,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[DonationResponse]:
    selection = cast(Select[tuple[BenefitGrant]], select(BenefitGrant).join(Player))  # pyright: ignore[reportInvalidCast]
    selection = filter_donations(selection, ckey, discord_id, cause, scope, active_only)
    page_data = paginate_selection(session, selection, request, page, page_size)

    return PaginatedResponse[DonationResponse](
        items=[grant_response(grant) for grant in page_data.items],
        total=page_data.total,
        page=page_data.page,
        page_size=page_data.page_size,
        next_page=page_data.next_page,
        previous_page=page_data.previous_page,
        next_page_path=page_data.next_page_path,
        previous_page_path=page_data.previous_page_path,
    )


@router.get("/{id}", status_code=status.HTTP_200_OK)
async def get_donation_by_id(session: SessionDep, id: int) -> DonationResponse | None:
    grant = session.exec(select(BenefitGrant).where(BenefitGrant.id == id)).first()
    return grant_response(grant) if grant else None


async def create_donations_helper(session: SessionDep, donations: list[BenefitGrant]) -> list[BenefitGrant]:
    session.add_all(donations)
    session.commit()
    for donation in donations:
        session.refresh(donation)
        logger.info("Donation created: %s", donation.model_dump_json())
    return donations


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_bearer)],
    responses={
        status.HTTP_201_CREATED: {"description": "Whitelist created"},
        status.HTTP_404_NOT_FOUND: {"description": "Player not found"},
    },
)
async def create_donation_by_discord(
    session: SessionDep, new_donation: NewDonationDiscord
) -> list[DonationResponse]:
    """Creating a new donation from any other identifier doesnt make much sense."""
    player = await get_or_create_player_by_discord_id(session, new_donation.discord_id)

    fan_out = new_donation.scope == "*"
    scopes = (
        session.exec(select(BenefitsScope.name).where(BenefitsScope.active, BenefitsScope.name != "*")).all()
        if fan_out
        else [new_donation.scope]
    )
    if not scopes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active scopes available")

    donations: list[BenefitGrant] = []
    for grant_scope in scopes:
        policy_tier = await resolve_benefit_source(session, new_donation.cause, grant_scope)
        tier = policy_tier if policy_tier is not None else new_donation.tier
        if tier is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tier is required for this grant")
        donations.append(
            BenefitGrant(
                player_id=player.id,  # pyright: ignore[reportArgumentType]
                tier=tier,
                cause=new_donation.cause,
                scope=grant_scope,
                issue_time=utcnow2(),
                expiration_time=utcnow2() + timedelta(days=new_donation.duration_days),
                valid=True,
            )
        )

    grants = await create_donations_helper(session, donations)
    return [grant_response(grant) for grant in grants]


@router.patch("/{id}", status_code=status.HTTP_200_OK, dependencies=[Depends(verify_bearer)])
async def update_donation(
    session: SessionDep, id: int, donation_patch: DonationPatch
) -> DonationResponse:  # pylint: disable=redefined-builtin
    grant = session.exec(select(BenefitGrant).where(BenefitGrant.id == id)).first()
    if not grant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")

    update_data = donation_patch.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(grant, key, value)

    session.commit()
    session.refresh(grant)
    return grant_response(grant)
