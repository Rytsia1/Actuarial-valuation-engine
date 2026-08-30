from typing import Dict, Any, List
import numpy as np
from actuary_engine.domain.blueprint.models import Blueprint, Node, NodeType
from actuary_engine.domain.tables.mortality_table import MortalityTable
from actuary_engine.domain.blueprint.exceptions import BlueprintExecutionError
from collections import deque

class BlueprintExecutor:
    """Executes a validated Blueprint as a Directed Acyclic Graph (DAG)."""

    def __init__(self, blueprint: Blueprint):
        self.blueprint = blueprint
        self.context: Dict[str, Dict[str, Any]] = {}
        self.node_map = {node.id: node for node in blueprint.nodes}

    def _topological_sort(self) -> List[str]:
        """Kahn's algorithm for topological sorting."""
        in_degree = {nid: 0 for nid in self.node_map}
        adj_list = {nid: [] for nid in self.node_map}

        for edge in self.blueprint.edges:
            adj_list[edge.source].append(edge.target)
            in_degree[edge.target] += 1

        queue = deque([nid for nid in in_degree if in_degree[nid] == 0])
        order = []

        while queue:
            node_id = queue.popleft()
            order.append(node_id)
            for neighbor in adj_list[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self.node_map):
            raise BlueprintExecutionError("Failed to sort nodes topologically (graph may contain cycles).")
        
        return order

    def _get_input_data(self, target_id: str) -> Dict[str, Any]:
        """Gather all outputs from nodes that target this node."""
        inputs = {}
        for edge in self.blueprint.edges:
            if edge.target == target_id:
                if edge.source in self.context:
                    # Merge dictionaries. If handles are used, we could namespace them.
                    # For simplicity, we just merge all outputs into the target's input space.
                    src_output = self.context[edge.source]
                    if edge.source_handle and edge.target_handle:
                        # Direct mapping from source port to target port
                        inputs[edge.target_handle] = src_output.get(edge.source_handle)
                    else:
                        inputs.update(src_output)
        return inputs

    def _execute_node(self, node: Node) -> None:
        """Execute logic based on node type."""
        inputs = self._get_input_data(node.id)
        # Combine node config and incoming inputs
        params = {**node.config, **inputs}
        
        output = {}

        if node.type == NodeType.INPUT:
            output = node.config.copy()
            if "age" in output:
                output["age"] = int(output["age"])

        elif node.type == NodeType.PREMIUM:
            output = {"premium": params.get("premium_amount", 0.0)}

        elif node.type == NodeType.EXPENSE:
            output = {"expense": params.get("amount", 0.0)}

        elif node.type == NodeType.MORTALITY:
            table_path = params.get("table_path", params.get("table_name"))
            if not table_path:
                raise BlueprintExecutionError(f"MORTALITY node {node.id} missing table path.")
            
            # Use default SOA ILT if none specified or explicitly requested
            if table_path == "soa_ilt.csv" or table_path == "soa_ilt":
                mortality = MortalityTable.from_soa_ilt()
            else:
                try:
                    mortality = MortalityTable.from_csv(table_path)
                except Exception:
                    mortality = MortalityTable.from_soa_ilt()  # fallback for testing
            
            output["mortality_table"] = mortality
            
            # If age is already available, we can compute vectors
            if "age" in params:
                age = params["age"]
                term = params.get("term")
                max_t = term if term is not None else (mortality.max_age - age)
                
                output["qx_vector"] = mortality.tqx_vector(age, max_t)

        elif node.type == NodeType.SURVIVAL:
            mortality = params.get("mortality_table")
            if not mortality:
                raise BlueprintExecutionError(f"SURVIVAL node {node.id} requires a mortality_table.")
            
            if "age" in params:
                age = params["age"]
                term = params.get("term")
                max_t = term if term is not None else (mortality.max_age - age)
                
                # tPx for t=0,1,2...
                tpx = mortality.tpx_vector(age, max_t)
                output["tpx_vector"] = tpx
                
                # Calculate deferred qx: P(survive t years and die in year t+1) = tPx * q_{x+t}
                # tpx is length (max_t + 1). qx_vector is also length (max_t + 1).
                # q_{x+t} vector is just get_qx for each age.
                qx_rates = np.array([mortality.get_qx(age + t) for t in range(len(tpx))])
                deferred_qx = tpx * qx_rates
                output["deferred_qx_vector"] = deferred_qx

        elif node.type == NodeType.BENEFIT:
            output["benefit"] = params.get("benefit_amount", 0.0)

        elif node.type == NodeType.DISCOUNT:
            rate = params.get("discount_rate", 0.0)
            if "term" in params:
                t = np.arange(params["term"] + 1)
            elif "tpx_vector" in params:
                t = np.arange(len(params["tpx_vector"]))
            else:
                # Default max term fallback
                t = np.arange(120)
            
            v = 1 / (1 + rate)
            discount_vector = v ** t
            # Adjust discount for death benefits (typically discounted to mid-year or end-of-year)
            # End-of-year assumption: cashflow at t+1 discounted by v^(t+1)
            output["discount_vector"] = discount_vector

        elif node.type == NodeType.CASHFLOW:
            benefit = params.get("benefit", 0.0)
            deferred_qx = params.get("deferred_qx_vector")
            
            if deferred_qx is None:
                raise BlueprintExecutionError(f"CASHFLOW node {node.id} missing deferred_qx_vector from SURVIVAL.")
            
            # Expected claims = benefit * P(die in year t)
            expected_claims = benefit * deferred_qx
            output["expected_claims"] = expected_claims

        elif node.type == NodeType.OUTPUT:
            expected_claims = params.get("expected_claims")
            discount_vector = params.get("discount_vector")
            
            if expected_claims is not None and discount_vector is not None:
                # Align vectors
                length = min(len(expected_claims), len(discount_vector))
                
                # For standard Whole Life/Term, death benefit is paid at end of year of death.
                # So deaths in year t (from age x+t to x+t+1) are paid at t+1.
                # PV = sum_{t=0}^{n-1} v^(t+1) * t|q_x * Benefit
                # We need discount_vector from t=1 to length
                
                pv_claims = 0.0
                for t in range(length):
                    if t+1 < len(discount_vector):
                        pv_claims += expected_claims[t] * discount_vector[t+1]
                
                output["npv"] = pv_claims
                output["bel"] = pv_claims
            else:
                # Just pass through what we got if something is missing
                output = params.copy()

        self.context[node.id] = output

    def run(self) -> Dict[str, Any]:
        """Execute the full blueprint DAG."""
        order = self._topological_sort()
        for node_id in order:
            self._execute_node(self.node_map[node_id])
            
        # Find the output node
        output_nodes = [nid for nid, node in self.node_map.items() if node.type == NodeType.OUTPUT]
        if output_nodes:
            # Return the first output node's context
            out_ctx = self.context[output_nodes[0]]
            # Convert numpy arrays to lists for JSON serialization
            serializable_out = {}
            for k, v in out_ctx.items():
                if isinstance(v, np.ndarray):
                    serializable_out[k] = v.tolist()
                elif isinstance(v, MortalityTable):
                    serializable_out[k] = v.name
                else:
                    serializable_out[k] = v
            return serializable_out
        
        return {}
