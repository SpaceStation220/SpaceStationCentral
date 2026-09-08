from app.database.models import BenefitGrant, PlayerBase, Whitelist, WhitelistBan


# region Get
class PlayerNested(PlayerBase):
    whitelists: list[Whitelist]
    whitelists_issued: list[Whitelist]

    whitelist_bans: list[WhitelistBan]
    whitelist_bans_issued: list[WhitelistBan]

    donations: list[BenefitGrant]


# endregion
