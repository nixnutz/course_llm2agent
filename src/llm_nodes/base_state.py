from pydantic import BaseModel, ConfigDict


class BaseState(BaseModel):
    model_config = ConfigDict(extra="forbid")
