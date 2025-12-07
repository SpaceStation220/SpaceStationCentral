from pydantic import BaseModel


class NewBan(BaseModel):
    player_ckey: str
    admin_ckey: str
    reason: str | None = None
    server_type: str
    duration_hours: int | None = None
    bantype: str | None = None  # PERMABAN, JOB_PERMABAN, TEMPBAN, JOB_TEMPBAN
    job: str | None = None
    round_id: int | None = None
