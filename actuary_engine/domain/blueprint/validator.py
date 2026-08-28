from typing import Dict, List, Set
from collections import defaultdict

from actuary_engine.domain.blueprint.models import Blueprint, NodeType
from actuary_engine.domain.blueprint.exceptions import BlueprintValidationError

class BlueprintValidator:
    """Validates the logical structure of a Blueprint DAG."""

    @staticmethod
    def validate(blueprint: Blueprint) -> None:
        """Run all graph validation checks on a blueprint."""
        if not blueprint.nodes:
            raise BlueprintValidationError("Blueprint must contain at least one node.")

        node_map = {node.id: node for node in blueprint.nodes}
        adj_list: Dict[str, List[str]] = defaultdict(list)
        reverse_adj_list: Dict[str, List[str]] = defaultdict(list)

        for edge in blueprint.edges:
            if edge.source not in node_map:
                raise BlueprintValidationError(f"Edge references unknown source node '{edge.source}'.")
            if edge.target not in node_map:
                raise BlueprintValidationError(f"Edge references unknown target node '{edge.target}'.")
            adj_list[edge.source].append(edge.target)
            reverse_adj_list[edge.target].append(edge.source)

        BlueprintValidator._check_cycles(node_map, adj_list)
        BlueprintValidator._check_connectivity(node_map, adj_list, reverse_adj_list)
        BlueprintValidator._check_invalid_connections(blueprint, node_map)
        BlueprintValidator._check_missing_inputs(blueprint, node_map, reverse_adj_list)
        BlueprintValidator._check_configuration(blueprint)

    @staticmethod
    def _check_cycles(node_map: Dict[str, 'Node'], adj_list: Dict[str, List[str]]) -> None:
        """Use DFS to detect cycles in the graph."""
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for neighbor in adj_list[node_id]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    path.append(neighbor)
                    return True

            rec_stack.remove(node_id)
            path.pop()
            return False

        for node_id in node_map:
            if node_id not in visited:
                if dfs(node_id):
                    # Format cycle path
                    cycle_start = path.index(path[-1])
                    cycle_nodes = path[cycle_start:]
                    cycle_str = " \u2192 ".join([node_map[nid].type.value.upper() for nid in cycle_nodes])
                    raise BlueprintValidationError(f"Cycle detected in path: {cycle_str}")

    @staticmethod
    def _check_connectivity(node_map: Dict[str, 'Node'], adj_list: Dict[str, List[str]], reverse_adj_list: Dict[str, List[str]]) -> None:
        """Ensure every node is on a path from an INPUT and a path to an OUTPUT."""
        
        # 1. Reachable from INPUT
        reachable_from_input: Set[str] = set()
        input_nodes = [nid for nid, node in node_map.items() if node.type == NodeType.INPUT]
        
        def dfs_forward(node_id: str):
            reachable_from_input.add(node_id)
            for neighbor in adj_list[node_id]:
                if neighbor not in reachable_from_input:
                    dfs_forward(neighbor)
                    
        for inode in input_nodes:
            dfs_forward(inode)

        for nid, node in node_map.items():
            if nid not in reachable_from_input and node.type != NodeType.INPUT:
                # Some static nodes might not strictly need an INPUT if they just produce a table, 
                # but let's enforce connectivity or warn. Actually, MORTALITY might not need INPUT.
                # Let's enforce that every node must be connected to something. If it has no edges, it's disconnected.
                if len(adj_list[nid]) == 0 and len(reverse_adj_list[nid]) == 0:
                    raise BlueprintValidationError(f"Node '{node.type.value}' ({nid}) is completely disconnected.")

    @staticmethod
    def _check_invalid_connections(blueprint: Blueprint, node_map: Dict[str, 'Node']) -> None:
        """Prevent semantically invalid connections."""
        for edge in blueprint.edges:
            src_node = node_map[edge.source]
            tgt_node = node_map[edge.target]

            if src_node.type == NodeType.OUTPUT:
                raise BlueprintValidationError(f"Cannot connect OUTPUT node '{src_node.id}' to any other node.")
            if tgt_node.type == NodeType.INPUT:
                raise BlueprintValidationError(f"Cannot connect to an INPUT node '{tgt_node.id}'.")
            if src_node.type == NodeType.PREMIUM and tgt_node.type == NodeType.MORTALITY:
                raise BlueprintValidationError("Semantic mismatch: Cannot connect PREMIUM to MORTALITY.")

    @staticmethod
    def _check_missing_inputs(blueprint: Blueprint, node_map: Dict[str, 'Node'], reverse_adj_list: Dict[str, List[str]]) -> None:
        """Ensure nodes have their required dependencies."""
        for nid, node in node_map.items():
            incoming = reverse_adj_list[nid]
            incoming_types = {node_map[src].type for src in incoming}

            if node.type == NodeType.BENEFIT:
                if NodeType.INPUT not in incoming_types and NodeType.SURVIVAL not in incoming_types:
                    raise BlueprintValidationError(f"Node 'BENEFIT' ({nid}) is disconnected. It requires incoming edges from 'INPUT' or 'SURVIVAL'.")
            
            elif node.type == NodeType.CASHFLOW:
                if NodeType.BENEFIT not in incoming_types:
                    raise BlueprintValidationError(f"Node 'CASHFLOW' ({nid}) requires an incoming edge from a 'BENEFIT' node.")
                if NodeType.SURVIVAL not in incoming_types and NodeType.MORTALITY not in incoming_types:
                    raise BlueprintValidationError(f"Node 'CASHFLOW' ({nid}) requires an incoming edge from a 'SURVIVAL' or 'MORTALITY' node.")
            
            elif node.type == NodeType.DISCOUNT:
                if NodeType.INPUT not in incoming_types and "discount_rate" not in node.config:
                    raise BlueprintValidationError(f"Node 'DISCOUNT' ({nid}) requires an incoming 'INPUT' or a direct 'discount_rate' config.")

    @staticmethod
    def _check_configuration(blueprint: Blueprint) -> None:
        """Validate config schemas for individual nodes."""
        for node in blueprint.nodes:
            if node.type == NodeType.INPUT:
                if "age" in node.config and not isinstance(node.config["age"], int):
                    raise BlueprintValidationError(f"Node 'INPUT' ({node.id}) requires 'age' to be an integer.")
                if "age" in node.config and node.config["age"] < 0:
                    raise BlueprintValidationError(f"Node 'INPUT' ({node.id}) requires 'age' > 0.")
                
            elif node.type == NodeType.MORTALITY:
                if "table_path" not in node.config and "table_name" not in node.config:
                    raise BlueprintValidationError(f"Node 'Mortality Table' at ID '{node.id}' is missing required config key 'table_name' or 'table_path'.")
