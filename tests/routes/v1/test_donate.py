import pytest
from app.database.models import BenefitGrant, BenefitPolicy, BenefitsScope
from app.routes.v1.donate import resolve_benefit_source
from app.schemas.v1.donate import DonationResponse
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session


def add_scope(session: Session, name: str) -> None:
    session.add(BenefitsScope(name=name, active=True))
    session.commit()


async def test_no_cause_with_concrete_scope_has_no_tier(db_session: Session) -> None:
    assert await resolve_benefit_source(db_session, None, "project-a") is None


async def test_cause_resolves_exact_active_policy(db_session: Session) -> None:
    add_scope(db_session, "project-a")
    db_session.add(BenefitPolicy(cause="admin", scope="project-a", benefit_tier=5, active=True))
    db_session.commit()

    assert await resolve_benefit_source(db_session, "admin", "project-a") == 5


async def test_cause_falls_back_to_default_policy(db_session: Session) -> None:
    add_scope(db_session, "*")
    add_scope(db_session, "project-a")
    db_session.add(BenefitPolicy(cause="admin", scope="*", benefit_tier=3, active=True))
    db_session.commit()

    assert await resolve_benefit_source(db_session, "admin", "project-a") == 3


async def test_exact_inactive_policy_does_not_fall_back(db_session: Session) -> None:
    add_scope(db_session, "*")
    add_scope(db_session, "project-a")
    db_session.add(BenefitPolicy(cause="admin", scope="*", benefit_tier=3, active=True))
    db_session.add(BenefitPolicy(cause="admin", scope="project-a", benefit_tier=5, active=False))
    db_session.commit()

    with pytest.raises(HTTPException):
        await resolve_benefit_source(db_session, "admin", "project-a")


def test_response_exposes_normalized_source() -> None:
    grant = BenefitGrant(id=1, player_id=2, tier=5, cause="admin", scope="project-a")

    response = DonationResponse.model_validate(grant, from_attributes=True)
    assert response.cause == "admin"
    assert response.scope == "project-a"


def test_read_benefit_scopes(client: TestClient, db_session: Session) -> None:
    add_scope(db_session, "project-a")

    response = client.get("policies/benefits/scopes")

    assert response.status_code == 200
    assert response.json()["items"] == [{"name": "project-a", "active": True}]


def test_read_benefit_policies(client: TestClient, db_session: Session) -> None:
    add_scope(db_session, "project-a")
    db_session.add(BenefitPolicy(cause="admin", scope="project-a", benefit_tier=5, active=True))
    db_session.commit()

    response = client.get("policies/benefits", params={"cause": "admin", "scope": "project-a"})

    assert response.status_code == 200
    assert response.json()["items"] == [
        {"cause": "admin", "scope": "project-a", "benefit_tier": 5, "active": True}
    ]


def test_wildcard_scope_creates_one_grant_per_active_scope(
    client: TestClient, db_session: Session, bearer: str
) -> None:
    add_scope(db_session, "project-a")
    add_scope(db_session, "project-b")

    response = client.post(
        "donates",
        headers={"Authorization": f"Bearer {bearer}"},
        json={"discord_id": "123456789", "tier": 3, "scope": "*"},
    )

    assert response.status_code == 201
    assert {item["scope"] for item in response.json()} == {"project-a", "project-b"}


def test_concrete_scope_still_returns_a_single_item_list(
    client: TestClient, db_session: Session, bearer: str
) -> None:
    add_scope(db_session, "project-a")

    response = client.post(
        "donates",
        headers={"Authorization": f"Bearer {bearer}"},
        json={"discord_id": "987654321", "tier": 3, "scope": "project-a"},
    )

    assert response.status_code == 201
    assert len(response.json()) == 1
    assert response.json()[0]["scope"] == "project-a"
