from datetime import datetime, timedelta

from discord import Color, Embed

from app.core.utils import utcnow2
from app.schemas.v1.ban import NewBan

def get_ban_embed(ban: NewBan, ban_id: int | None = None) -> Embed:
	"""
	Creates discord embed for bans (updated for duration_hours)
	"""
	# ban type
	bantype = ban.bantype
	if not bantype:
		if ban.job:
			bantype = "JOB_PERMABAN" if ban.duration_hours is None else "JOB_TEMPBAN"
		else:
			bantype = "PERMABAN" if ban.duration_hours is None else "TEMPBAN"

	# duration inner
	expiration_time = None

	if bantype == "PERMABAN":
		ban.duration_hours = None
		expiration_time = None

	elif ban.duration_hours is not None:
		expiration_time = utcnow2() + timedelta(hours=ban.duration_hours)
	else:
		expiration_time = None  # permanent

	# color and name
	match bantype:
		case "PERMABAN":
			ban_color = Color.red()
			ban_type_name = "Пермабан"
		case "JOB_PERMABAN":
			ban_color = Color.purple()
			ban_type_name = "Пермаджоббан"
		case "TEMPBAN":
			ban_color = Color.orange()
			ban_type_name = "Темпбан"
		case "JOB_TEMPBAN":
			ban_color = Color.blue()
			ban_type_name = "Джоббан"
		case _:
			ban_color = Color.default()
			ban_type_name = bantype

	# desc
	description_parts = [
		f"**Игрок:** {ban.player_ckey}",
		f"**Админ:** {ban.admin_ckey}",
	]

	# duration outer
	if ban.duration_hours is not None and ban.duration_hours > 0:
		hours = ban.duration_hours
		expiration_str = expiration_time.strftime('%Y-%m-%d %H:%M:%S')
		description_parts.append(f"**Длительность:** {hours} ч. до {expiration_str}")
	else:
		description_parts.append("**Длительность:** Навсегда")

	# reason
	if ban.reason:
		description_parts.append(f"**Причина:** {ban.reason}")

	# job
	if bantype in ("JOB_TEMPBAN", "JOB_PERMABAN") and ban.job:
		description_parts.append(f"**Роль:** {ban.job}")

	description = "\n".join(description_parts)

	# title
	title = f"**{ban_type_name}**"
	if ban_id is not None:
		title = f"**{ban_type_name} {ban_id}**"
		
    # round id
	if ban.round_id is not None:
		description_parts.append(f"**Раунд:** {ban.round_id}")
	description = "\n".join(description_parts)

	# embed
	embed = Embed(
		title=title,
		description=description,
		color=ban_color,
	)

	# footer
	ban_time = utcnow2()
	footer_text = f"{ban.server_type} - {ban_time.strftime('%Y-%m-%d %H:%M:%S')}"
	embed.set_footer(text=footer_text)

	return embed