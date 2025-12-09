from datetime import datetime, timedelta

from app.core.utils import utcnow2
from app.schemas.v1.ban import NewBan
from discord import Color, Embed


def determine_ban_type(ban: NewBan) -> str:
    """Determine the effective bantype based on ban info."""
    if ban.bantype:
        return ban.bantype

    # fallback safety mode
    if ban.job:
        return "JOB_PERMABAN" if ban.duration_hours is None else "JOB_TEMPBAN"

    return "PERMABAN" if ban.duration_hours is None else "TEMPBAN"

def get_ban_color_name(bantype: str) -> tuple[Color, str]:
    """Return the embed color and display name for a bantype."""
    match bantype:
        case "PERMABAN":
            return Color.red(), "Пермабан"
        case "JOB_PERMABAN":
            return Color.purple(), "Пермаджоббан"
        case "TEMPBAN":
            return Color.orange(), "Темпбан"
        case "JOB_TEMPBAN":
            return Color.blue(), "Джоббан"
        case _:
            return Color.default(), bantype

def build_description_parts(ban: NewBan, bantype: str, expiration_time: datetime | None) -> list[str]:
    """Build the description lines for the embed."""
    parts = [
        f"**Игрок:** {ban.player_ckey}",
        f"**Админ:** {ban.admin_ckey}",
    ]

    # duration
    if bantype in ("PERMABAN", "JOB_PERMABAN"):
        parts.append("**Длительность:** Навсегда")
    elif ban.duration_hours is not None and ban.duration_hours > 0:
        expiration_str = (
            expiration_time.strftime("%Y-%m-%d %H:%M:%S")
            if expiration_time else "unknown"
        )
        parts.append(f"**Длительность:** {ban.duration_hours} ч. до {expiration_str}")
    else:
        parts.append("**Длительность:** Навсегда")

    # reason
    if ban.reason:
        parts.append(f"**Причина:** {ban.reason}")

    # job
    if bantype in ("JOB_TEMPBAN", "JOB_PERMABAN") and ban.job:
        parts.append(f"**Роль:** {ban.job}")

    # round
    if ban.round_id is not None:
        parts.append(f"**Раунд:** {ban.round_id}")

    return parts


def get_ban_embed(ban: NewBan, ban_id: int | None = None) -> Embed:
    """Creates discord embed for bans (updated for duration_hours)."""
    # Determine type and expiration
    bantype = determine_ban_type(ban)

    expiration_time = None
    if bantype != "PERMABAN" and ban.duration_hours is not None:
        expiration_time = utcnow2() + timedelta(hours=ban.duration_hours)
    elif bantype == "PERMABAN":
        ban.duration_hours = None

    # Get color and title
    ban_color, ban_type_name = get_ban_color_name(bantype)

    # Build description
    description_parts = build_description_parts(ban, bantype, expiration_time)
    description = "\n".join(description_parts)

    # Title
    title = f"**{ban_type_name}**" if ban_id is None else f"**{ban_type_name} {ban_id}**"

    # Embed
    embed = Embed(title=title, description=description, color=ban_color)

    # Footer
    ban_time = utcnow2()
    embed.set_footer(text=f"{ban.server_type} - {ban_time.strftime('%Y-%m-%d %H:%M:%S')}")

    return embed
