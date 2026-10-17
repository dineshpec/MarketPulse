from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ScoutInput(BaseModel):
    business_idea: str
    city: str
    target_customer: str
    known_competitors: str = ""

    @field_validator("business_idea", "city", "target_customer")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("must not be empty")
        return v

    @field_validator("known_competitors")
    @classmethod
    def _strip(cls, v: str) -> str:
        return (v or "").strip()


class CrewResult(BaseModel):
    report_markdown: str
    pitch_deck_markdown: Optional[str] = None
    report_path: str
    warnings: list[str] = Field(default_factory=list)
