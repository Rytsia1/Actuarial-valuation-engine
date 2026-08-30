from typing import Dict, Any, List
import numpy as np
from actuary_engine.domain.blueprint.models import Blueprint, Node, NodeType
from actuary_engine.api.schemas import ContractGraphPayload, GraphNodeData, GraphEdgeData
from actuary_engine.valuation.graph_parser import ContractGraphSimulator
from actuary_engine.domain.blueprint.exceptions import BlueprintExecutionError

class BlueprintExecutor:
    """Executes a validated Blueprint by adapting it to the ContractGraphSimulator."""

    def __init__(self, blueprint: Blueprint):
        self.blueprint = blueprint

    def run(self) -> Dict[str, Any]:
        """Execute the full blueprint DAG using ContractGraphSimulator."""
        try:
            # Adapt Blueprint to ContractGraphPayload
            nodes = [
                GraphNodeData(
                    id=node.id,
                    type=node.type.value,
                    data=node.config,
                    position=node.position
                )
                for node in self.blueprint.nodes
            ]
            
            edges = [
                GraphEdgeData(
                    id=edge.id,
                    source=edge.source,
                    target=edge.target,
                    sourceHandle=edge.source_handle,
                    targetHandle=edge.target_handle
                )
                for edge in self.blueprint.edges
            ]
            
            payload = ContractGraphPayload(
                contract_id=str(self.blueprint.id),
                nodes=nodes,
                edges=edges
            )
            
            simulator = ContractGraphSimulator()
            response = simulator.simulate(payload)
            
            # The simulator returns a SimulateGraphResponse which is a Pydantic model.
            # The frontend expects 'full_output' in the exact shape of SimulateGraphResponse.
            return response.model_dump()
            
        except Exception as e:
            raise BlueprintExecutionError(f"Failed to execute blueprint graph: {str(e)}")

