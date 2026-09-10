from app.database.models import BenefitGrant, BenefitPolicy, BenefitsScope, Player
from app.routes.v1.donate import resolve_benefit_source
from app.schemas.v1.donate import DonationResponse
from fastapi.testclient import TestClient
from sqlmodel import Session, select


def add_scope(session: Session, name: str, active: bool = True) -> None:
    session.add(BenefitsScope(name=name, active=active))
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


async def test_inactive_exact_policy_falls_back_to_active_wildcard(db_session: Session) -> None:
    add_scope(db_session, "*")
    add_scope(db_session, "project-a")
    db_session.add(BenefitPolicy(cause="admin", scope="*", benefit_tier=3, active=True))
    db_session.add(BenefitPolicy(cause="admin", scope="project-a", benefit_tier=5, active=False))
    db_session.commit()

    assert await resolve_benefit_source(db_session, "admin", "project-a") == 3


async def test_missing_policy_returns_no_tier(db_session: Session) -> None:
    add_scope(db_session, "project-a")

    assert await resolve_benefit_source(db_session, "admin", "project-a") is None


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
        json={"discord_id": "123456789", "tier": 3, "scope": ["*"]},
    )

    assert response.status_code == 201
    assert {item["scope"] for item in response.json()} == {"project-a", "project-b"}


def test_request_tier_overrides_policy_tier(
    client: TestClient, db_session: Session, bearer: str
) -> None:
    add_scope(db_session, "project-a")
    db_session.add(BenefitPolicy(cause="special_event", scope="project-a", benefit_tier=3, active=True))
    db_session.commit()

    response = client.post(
        "donates",
        headers={"Authorization": f"Bearer {bearer}"},
        json={"discord_id": "666666666", "cause": "special_event", "tier": 7, "scope": ["project-a"]},
    )

    assert response.status_code == 201
    assert response.json()[0]["tier"] == 7


def test_wildcard_scope_uses_request_tier_without_policy(
    client: TestClient, db_session: Session, bearer: str
) -> None:
    add_scope(db_session, "project-a")
    add_scope(db_session, "project-b")

    response = client.post(
        "donates",
        headers={"Authorization": f"Bearer {bearer}"},
        json={"discord_id": "555555555", "cause": "special_event", "tier": 7, "scope": ["*"]},
    )

    assert response.status_code == 201
    assert {item["scope"] for item in response.json()} == {"project-a", "project-b"}
    assert {item["tier"] for item in response.json()} == {7}


def test_concrete_scope_still_returns_a_single_item_list(
    client: TestClient, db_session: Session, bearer: str
) -> None:
    add_scope(db_session, "project-a")

    response = client.post(
        "donates",
        headers={"Authorization": f"Bearer {bearer}"},
        json={"discord_id": "987654321", "tier": 3, "scope": ["project-a"]},
    )

    assert response.status_code == 201
    assert len(response.json()) == 1
    assert response.json()[0]["scope"] == "project-a"


def test_multiple_scopes_create_one_grant_per_scope(
    client: TestClient, db_session: Session, bearer: str
) -> None:
    add_scope(db_session, "project-a")
    add_scope(db_session, "project-b")

    response = client.post(
        "donates",
        headers={"Authorization": f"Bearer {bearer}"},
        json={"discord_id": "111111111", "tier": 3, "scope": ["project-a", "project-b"]},
    )

    assert response.status_code == 201
    assert {item["scope"] for item in response.json()} == {"project-a", "project-b"}


def test_mixed_wildcard_and_explicit_scopes_are_unioned(
    client: TestClient, db_session: Session, bearer: str
) -> None:
    add_scope(db_session, "project-a")
    add_scope(db_session, "project-b")

    response = client.post(
        "donates",
        headers={"Authorization": f"Bearer {bearer}"},
        json={"discord_id": "222222222", "tier": 3, "scope": ["project-a", "project-a", "*"]},
    )

    assert response.status_code == 201
    assert len(response.json()) == 2
    assert {item["scope"] for item in response.json()} == {"project-a", "project-b"}


def test_unknown_scope_rejects_without_inserts(
    client: TestClient, db_session: Session, bearer: str
) -> None:
    add_scope(db_session, "project-a")

    response = client.post(
        "donates",
        headers={"Authorization": f"Bearer {bearer}"},
        json={"discord_id": "333333333", "tier": 3, "scope": ["project-a", "missing"]},
    )

    assert response.status_code == 403
    assert db_session.exec(select(Player)).all() == []
    assert db_session.exec(select(BenefitGrant)).all() == []


def test_inactive_scope_rejects_without_inserts(
    client: TestClient, db_session: Session, bearer: str
) -> None:
    add_scope(db_session, "project-a", active=False)

    response = client.post(
        "donates",
        headers={"Authorization": f"Bearer {bearer}"},
        json={"discord_id": "444444444", "tier": 3, "scope": ["project-a"]},
    )

    assert response.status_code == 403
    assert db_session.exec(select(Player)).all() == []
    assert db_session.exec(select(BenefitGrant)).all() == []
