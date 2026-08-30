from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from actuary_engine.infrastructure.database import get_db
from actuary_engine.services.workflow_orchestrator import ValuationWorkflow
from actuary_engine.api.schemas.project import CreateProjectRequest
from actuary_engine.api.schemas.workflow import CreateContractRequest, CreateAssumptionSetRequest, WorkflowStateResponse

router = APIRouter(prefix="/workflow", tags=["Valuation Workflow"])

@router.post("/start", response_model=WorkflowStateResponse)
def start_workflow(request: CreateProjectRequest, db: Session = Depends(get_db)):
    """Initialize a new project and workflow."""
    from actuary_engine.services.project_service import ProjectService
    service = ProjectService(db)
    project = service.create_project(request.name, request.description)
    
    workflow = ValuationWorkflow(db, project.id)
    state = workflow.transition_to_next_step()
    return {"project_id": project.id, **state}

@router.get("/{project_id}/state", response_model=WorkflowStateResponse)
def get_workflow_state(project_id: UUID, db: Session = Depends(get_db)):
    """Get the current workflow step and required data for the UI."""
    workflow = ValuationWorkflow(db, project_id)
    try:
        state = workflow.transition_to_next_step()
        return {"project_id": project_id, **state}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{project_id}/contract", response_model=WorkflowStateResponse)
def add_contract(project_id: UUID, request: CreateContractRequest, db: Session = Depends(get_db)):
    """Create a contract and advance the workflow."""
    from actuary_engine.infrastructure.repositories import ContractRepository
    repo = ContractRepository(db)
    contract = repo.create(
        project_id=project_id,
        name=request.name,
        product_type=request.product_type,
        blueprint_json=request.blueprint_json or {}
    )
    workflow = ValuationWorkflow(db, project_id)
    state = workflow.transition_to_next_step()
    return {"project_id": project_id, "contract_id": contract.id, **state}


