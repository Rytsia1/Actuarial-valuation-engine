from fastapi import APIRouter, HTTPException
from actuary_engine.domain.blueprint.models import Blueprint
from actuary_engine.domain.blueprint.validator import BlueprintValidator
from actuary_engine.domain.blueprint.executor import BlueprintExecutor
from actuary_engine.domain.blueprint.exceptions import BlueprintValidationError, BlueprintExecutionError

router = APIRouter(tags=["Blueprint"])

@router.post("/execute")
async def execute_blueprint(blueprint: Blueprint):
    """
    Validates and executes a UI-generated Blueprint DAG.
    """
    try:
        BlueprintValidator.validate(blueprint)
    except BlueprintValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    try:
        executor = BlueprintExecutor(blueprint)
        result = executor.run()
        return result
    except BlueprintExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal engine error: {str(e)}")
