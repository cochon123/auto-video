"""Agent registry for configuration mapping."""

from enum import Enum


class AgentName(str, Enum):
    """Standard agent names for configuration mapping."""

    DIRECTOR = "director"
    RESEARCHER = "researcher"
    SCRIPTWRITER = "scriptwriter"
    REVIEWER = "reviewer"
    VISUAL_CURATOR = "visual_curator"

    @classmethod
    def all(cls) -> list[str]:
        return [a.value for a in cls]
