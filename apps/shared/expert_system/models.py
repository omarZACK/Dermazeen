"""
Enhanced Data models with Confidence Factors, Multi-Select Support, and Melasma
"""
from experta import Fact,Field

# Enhanced Facts with Confidence Factors
class UserResponse(Fact):
    """Stores user answers to questions"""
    question_id = Field(str)
    value = Field(object)

class ConditionExcluded(Fact):
    pass

class CurrentPhase(Fact):
    """Current questioning phase"""
    phase = Field(str)


class QuestionAsked(Fact):
    """Track which questions have been asked"""
    question_id = Field(str)

class ConditionScore(Fact):
    """Score for each skin condition with confidence factor"""
    pass


class SkinProfile(Fact):
    """User's skin profile characteristics"""
    pass


class RecommendationGenerated(Fact):
    """Flag that recommendations have been generated"""
    pass

class MedicalReferralRequired(Fact):
    """Flag that immediate medical referral is required"""
    pass


class ConfidenceFactor(Fact):
    """Confidence factor for rules and conditions"""
    pass

class LifestyleDataProcessed(Fact):
    pass