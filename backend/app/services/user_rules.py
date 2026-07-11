"""Builds a RulesConfig from a User's customization fields, shared by SubjectService/ReviewService."""

from app.models.user import User
from app.services.adaptive_engine import RulesConfig, DEFAULT_RULES, ladders_from_dict


def get_rules(user: User) -> RulesConfig:
    ladders = ladders_from_dict(user.custom_ladders) if user.custom_ladders else DEFAULT_RULES.ladders
    return RulesConfig(
        ladders=ladders,
        no_revision_enabled=user.no_revision_enabled,
        no_revision_weekday=user.no_revision_weekday,
    )
