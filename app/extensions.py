"""Extensions registry
All extensions here are used as singletons and
initialized in application factory
"""
from app.constants import (
    FEEDBACK_MAX_RATING,
    FEEDBACK_MIN_RATING
)
from app.feedback_lambda import Feedback

feedback = Feedback(FEEDBACK_MAX_RATING, FEEDBACK_MIN_RATING)
