from app.database.models import BenefitGrantBase, Player


# region Get
class DonationNested(BenefitGrantBase):
    player: Player


# endregion
