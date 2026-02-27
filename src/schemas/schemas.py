import pydantic
from pydantic import field_validator
# from src.DOCUMENTATION.DATA_DICTIONARIES.CHALLENGE_TYPES import 

class GameStateInput(pydantic.BaseModel):
    spread: float #clip to +/- 20
    period: int #btwn 1 and 10
    minute: int #btwn 0 and 12
    second: int #btwn 0 and 60
    score_margin: int #clip to +/- 20
    challenge_type: str #

    @field_validator('spread')
    @classmethod
    def validate_spread(cls, v):
        """Clip spread to +/- 20"""
        return max(-20, min(20, v))

    @field_validator('period')
    @classmethod
    def validate_period(cls, v):
        """Period must be between 1 and 10"""
        if not 1 <= v <= 10:
            raise ValueError('period must be between 1 and 10')
        return v

    @field_validator('minute')
    @classmethod
    def validate_minute(cls, v):
        """Minute must be between 0 and 12"""
        if not 0 <= v <= 12:
            raise ValueError('minute must be between 0 and 12')
        return v

    @field_validator('second')
    @classmethod
    def validate_second(cls, v):
        """Second must be between 0 and 60"""
        if not 0 <= v <= 60:
            raise ValueError('second must be between 0 and 60')
        return v

    @field_validator('score_margin')
    @classmethod
    def validate_score_margin(cls, v):
        """Clip score_margin to +/- 20"""
        return max(-20, min(20, v))

    @property
    def time_elapsed(self):
        return (self.period - 1) * 720 + (12-self.minute) * 60 + (60-self.second)
    
    