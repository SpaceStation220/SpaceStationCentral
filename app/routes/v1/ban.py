import logging
from typing import Any

import aiohttp
from discord import Webhook
from fastapi import APIRouter, Depends, status

from app.core.config import get_config
from app.deps import verify_bearer
from app.helpers.ban import get_ban_embed
from app.schemas.v1.ban import NewBan


logger = logging.getLogger(__name__)

ban_router = APIRouter(prefix="/bans", tags=["Ban"])

@ban_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_bearer)],
)
async def ban_created(new_ban: NewBan) -> dict[str, Any]:
    #logger.info("Ban created: %s", new_ban.model_dump_json())

    config = get_config()

    if config.general.discord_public_webhook:
        try:
            embed = get_ban_embed(new_ban)

            async with aiohttp.ClientSession() as session:
                webhook = Webhook.from_url(
                    config.general.discord_public_webhook,
                    session=session
                )
                await webhook.send(embed=embed)

        except aiohttp.ClientError as e:
            logger.error("Failed to send ban notification to public webhook: %s", e)

    return {"status": "ok"}
