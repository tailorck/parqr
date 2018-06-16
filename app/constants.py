from enum import Enum


SCORE_THRESHOLD = 0.1
COURSE_PARSE_TRAIN_INTERVAL_S = 120  # seconds
COURSE_MODEL_RELOAD_DELAY_S = 150  # seconds


class TFIDF_MODELS(Enum):
    POST = 0
    I_ANSWER = 1
    S_ANSWER = 2
    FOLLOWUP = 3
