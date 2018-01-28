from enum import Enum


SCORE_THRESHOLD = 0.1


class TFIDF_MODELS(Enum):
    POST = 0
    I_ANSWER = 1
    S_ANSWER = 2
    FOLLOWUP = 3
