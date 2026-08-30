from enum import Enum
from uuid import UUID
from sqlalchemy.orm import Session
from actuary_engine.infrastructure.repositories import ProjectRepository, ContractRepository, AssumptionSetRepository, ValuationRunRepository
from actuary_engine.services.blueprint_service import BlueprintService
from actuary_engine.services.valuation_service import ValuationService
from actuary_engine.domain.blueprint.models import Blueprint
from actuary_engine.core.exceptions import InvalidBlueprintError, WorkflowStateError

class WorkflowStep(str, Enum):
    PROJECT = "project"
    CONTRACT = "contract"
    BLUEPRINT = "blueprint"

class ValuationWorkflow:
    """
    Orchestrates the valuation project setup lifecycle.
    Tracks which step the user is currently on (up to launching the builder).
    """
    def __init__(self, db: Session, project_id: UUID, background_tasks=None):
        self.db = db
        self.project_id = project_id
        self.background_tasks = background_tasks
        self.project_repo = ProjectRepository(db)
        self.contract_repo = ContractRepository(db)
        self._current_step = WorkflowStep.PROJECT

    def get_current_step(self) -> WorkflowStep:
        """Determine the current step based on existing data."""
        project = self.project_repo.get(self.project_id)
        if not project:
            return WorkflowStep.PROJECT
        
        contracts = self.contract_repo.list_by_project(self.project_id)
        if not contracts:
            return WorkflowStep.CONTRACT
        
        # If there's a contract, assume blueprint step is active or complete
        return WorkflowStep.BLUEPRINT

    def transition_to_next_step(self) -> dict:
        """
        Validates the current state and returns the current step.
        """
        current = self.get_current_step()
        
        if current == WorkflowStep.PROJECT:
            return {"step": WorkflowStep.PROJECT}

        elif current == WorkflowStep.CONTRACT:
            return {"step": WorkflowStep.CONTRACT, "project_id": self.project_id}

        elif current == WorkflowStep.BLUEPRINT:
            contracts = self.contract_repo.list_by_project(self.project_id)
            return {"step": WorkflowStep.BLUEPRINT, "contract_id": contracts[0].id}

        return {"step": current}

