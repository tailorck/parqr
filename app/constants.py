from enum import Enum


SCORE_THRESHOLD = 0.1
COURSE_PARSE_TRAIN_TIMEOUT_S = 600  # seconds
COURSE_PARSE_TRAIN_INTERVAL_S = 1800  # seconds
COURSE_MODEL_RELOAD_DELAY_S = 3600  # seconds

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

POST_AGE_SIGMOID_OFFSET = 7
POST_MAX_AGE_DAYS = 21

FEEDBACK_MAX_RATING = 1
FEEDBACK_MIN_RATING = -1


class TFIDF_MODELS(Enum):
    POST = 0
    I_ANSWER = 1
    S_ANSWER = 2
    FOLLOWUP = 3
