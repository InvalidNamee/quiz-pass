from pydantic import BaseModel


class AIGenerationWorkflowCreatedOut(BaseModel):
    workflow_id: int
    bank_id: int
    job_id: int
