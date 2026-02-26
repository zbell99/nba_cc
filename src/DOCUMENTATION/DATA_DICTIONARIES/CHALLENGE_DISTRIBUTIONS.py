from enum import Enum
from scipy.stats import poisson, beta


class ChallengeType(str, Enum):
    ALREADY_IN_YOUR_FAVOR = None
    OOB = "oob_challenge"
    NOFOUL2_KEEPBALL = "nofoul2_keepBall"
    NOFOUL2_JUMPBALL = "nofoul2_jumpBall"
    NOFOUL2_LOSEBALL = "nofoul2_loseBall"
    NOFOUL3_KEEPBALL = "nofoul3_keepBall"
    NOFOUL3_JUMPBALL = "nofoul3_jumpBall"
    NOFOUL3_LOSEBALL = "nofoul3_loseBall"
    NOGOALTEND = "nogoaltend"
    NOAND1 = "noand1"


class CallType:
    def __init__(self, challenge_type: ChallengeType, p: float):
        self.challenge_type = challenge_type
        self.p = p


class CallCategory:
    def __init__(self, clear_correct: float, ambiguous: float, clear_incorrect: float):
        self.clear_correct = clear_correct
        self.ambiguous = ambiguous
        self.clear_incorrect = clear_incorrect


class CallConfidence:
    def __init__(self, clear_correct, ambiguous, clear_incorrect):
        self.clear_correct = clear_correct
        self.ambiguous = ambiguous
        self.clear_incorrect = clear_incorrect


class Challenge:
    def __init__(self, call_categories: CallCategory, call_confidences: CallConfidence, distribution):
        self.call_categories = call_categories
        self.call_confidences = call_confidences
        self.call_types = []  # to be defined in subclasses with specific challenge types and probabilities
        self.distribution = distribution


class OOBChallenge(Challenge):
    def __init__(self, min_per_time_period: float):
        self.call_categories = CallCategory(
            clear_correct=0.85,
            ambiguous=0.12,
            clear_incorrect=0.03
        )
        self.call_confidences = CallConfidence(
            clear_correct=beta(a=1, b=40),  # low overturn confidence for correct calls
            ambiguous=beta(a=5, b=4),      # uniform
            clear_incorrect=beta(a=40, b=1) # high overturn confidence for incorrect calls
        )
        self.call_types = [
            CallType(challenge_type=ChallengeType.ALREADY_IN_YOUR_FAVOR, p=0.5),  # Called in your favor, no need to challenge
            CallType(challenge_type=ChallengeType.OOB, p=0.5),  # Offense loses the two points, possession is a jump ball
        ]
        self.distribution = poisson(mu=1*min_per_time_period)  # example distribution for number of successful challenges based on RPM


class FoulChallenge(Challenge):
    def __init__(self, min_per_time_period: float):
        self.call_categories = CallCategory(
            clear_correct=0.80,
            ambiguous=0.15,
            clear_incorrect=0.05
        )
        self.call_confidences = CallConfidence(
            clear_correct=beta(a=1, b=15),  # low overturn confidence for correct calls
            ambiguous=beta(a=5, b=4),      # uniform
            clear_incorrect=beta(a=10, b=2) # high overturn confidence for incorrect calls
        )
        self.call_types = [
            CallType(challenge_type=ChallengeType.ALREADY_IN_YOUR_FAVOR, p=0.5),  # Called in your favor, no need to challenge
            CallType(challenge_type=ChallengeType.NOFOUL2_KEEPBALL, p=3*0.5/15),
            CallType(challenge_type=ChallengeType.NOFOUL2_JUMPBALL, p=0.5/15),
            CallType(challenge_type=ChallengeType.NOFOUL2_LOSEBALL, p=3*0.5/15),
            CallType(challenge_type=ChallengeType.NOFOUL3_KEEPBALL, p=2*0.5/15),
            CallType(challenge_type=ChallengeType.NOFOUL3_JUMPBALL, p=0.5/15),
            CallType(challenge_type=ChallengeType.NOFOUL3_LOSEBALL, p=2*0.5/15),
            CallType(challenge_type=ChallengeType.NOAND1, p=3*0.5/15),
        ]

        self.distribution = poisson(mu=0.8*min_per_time_period)  # example distribution for number of successful challenges based on RPM


class GoaltendChallenge(Challenge):
    def __init__(self, min_per_time_period: float):
        self.call_categories = CallCategory(
            clear_correct=0.85,
            ambiguous=0.12,
            clear_incorrect=0.03
        )
        self.call_confidences = CallConfidence(
            clear_correct=beta(a=1, b=40),  # low overturn confidence for correct calls
            ambiguous=beta(a=5, b=4),      # uniform
            clear_incorrect=beta(a=40, b=1) # high overturn confidence for incorrect calls
        )
        self.call_types = [
            CallType(challenge_type=ChallengeType.ALREADY_IN_YOUR_FAVOR, p=0.5),
            CallType(challenge_type=ChallengeType.NOGOALTEND, p=0.5),
        ]
        self.distribution = poisson(mu=0.02*min_per_time_period)

