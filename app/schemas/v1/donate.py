import datetime

from pydantic import BaseModel


class NewDonationBase(BaseModel):
    tier: int | None = None
    cause: str | None = None
    scope: str
    duration_days: int = 30


class DonationResponse(BaseModel):
    id: int
    player_id: int
    tier: int
    cause: str | None
    scope: str
    issue_time: datetime.datetime
    expiration_time: datetime.datetime
    valid: bool


class NewDonationDiscord(NewDonationBase):
    discord_id: str


class DonationPatch(BaseModel):
    expiration_time: datetime.datetime
