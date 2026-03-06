# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
N8N Workflow Parser

Parses N8N workflow JSON exports and extracts structure for conversion.

Usage:
    uv run .claude/skills/n8n-converter/scripts/parse_n8n.py --input workflow.json
    uv run .claude/skills/n8n-converter/scripts/parse_n8n.py --input workflow.json --output parsed.json
    cat workflow.json | uv run .claude/skills/n8n-converter/scripts/parse_n8n.py
"""

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class N8NNode:
    """Represents an N8N workflow node."""
    id: str
    name: str
    type: str
    type_version: float
    position: tuple[int, int]
    parameters: dict[str, Any]
    credentials: dict[str, Any] | None = None
    is_trigger: bool = False
    incoming: list[str] = field(default_factory=list)
    outgoing: list[str] = field(default_factory=list)


@dataclass
class N8NWorkflow:
    """Represents a parsed N8N workflow."""
    name: str
    id: str | None
    nodes: list[N8NNode]
    connections: dict[str, Any]
    trigger_node: N8NNode | None
    execution_order: list[str]
    settings: dict[str, Any]


def is_trigger_node(node_type: str) -> bool:
    """Check if a node type is a trigger node."""
    trigger_types = [
        "n8n-nodes-base.webhook",
        "n8n-nodes-base.cron",
        "n8n-nodes-base.scheduleTrigger",
        "n8n-nodes-base.manualTrigger",
        "n8n-nodes-base.emailTrigger",
        "n8n-nodes-base.emailReadImap",
        "n8n-nodes-base.rssFeedRead",
        "n8n-nodes-base.start",
        # Add more trigger types as needed
    ]
    return node_type in trigger_types or "Trigger" in node_type


def parse_node(node_data: dict) -> N8NNode:
    """Parse a single N8N node from JSON."""
    position = node_data.get("position", [0, 0])
    return N8NNode(
        id=node_data.get("id", node_data["name"]),
        name=node_data["name"],
        type=node_data["type"],
        type_version=node_data.get("typeVersion", 1),
        position=(position[0], position[1]),
        parameters=node_data.get("parameters", {}),
        credentials=node_data.get("credentials"),
        is_trigger=is_trigger_node(node_data["type"]),
    )


def build_connection_graph(connections: dict, nodes: dict[str, N8NNode]) -> None:
    """Build incoming/outgoing connections for each node."""
    for source_name, outputs in connections.items():
        if source_name not in nodes:
            continue

        source_node = nodes[source_name]

        # N8N connections structure: {nodeName: {main: [[{node: targetName, type: main, index: 0}]]}}
        for output_type, output_connections in outputs.items():
            for output_index, targets in enumerate(output_connections):
                for target in targets:
                    target_name = target.get("node")
                    if target_name and target_name in nodes:
                        source_node.outgoing.append(target_name)
                        nodes[target_name].incoming.append(source_name)


def get_execution_order(nodes: dict[str, N8NNode], trigger: N8NNode | None) -> list[str]:
    """Determine execution order using topological sort from trigger."""
    if not trigger:
        # No trigger found, return nodes in arbitrary order
        return list(nodes.keys())

    visited = set()
    order = []

    def dfs(node_name: str):
        if node_name in visited:
            return
        visited.add(node_name)

        node = nodes.get(node_name)
        if not node:
            return

        for next_node in node.outgoing:
            dfs(next_node)

        order.append(node_name)

    dfs(trigger.name)

    # Reverse to get correct execution order
    return list(reversed(order))


def parse_workflow(workflow_json: dict) -> N8NWorkflow:
    """Parse a complete N8N workflow from JSON."""
    nodes_list = workflow_json.get("nodes", [])
    connections = workflow_json.get("connections", {})

    # Parse all nodes
    nodes: dict[str, N8NNode] = {}
    trigger_node: N8NNode | None = None

    for node_data in nodes_list:
        node = parse_node(node_data)
        nodes[node.name] = node

        if node.is_trigger and trigger_node is None:
            trigger_node = node

    # Build connection graph
    build_connection_graph(connections, nodes)

    # Get execution order
    execution_order = get_execution_order(nodes, trigger_node)

    return N8NWorkflow(
        name=workflow_json.get("name", "Unnamed Workflow"),
        id=workflow_json.get("id"),
        nodes=list(nodes.values()),
        connections=connections,
        trigger_node=trigger_node,
        execution_order=execution_order,
        settings=workflow_json.get("settings", {}),
    )


def extract_expressions(parameters: dict, path: str = "") -> list[dict]:
    """Recursively extract N8N expressions from parameters."""
    expressions = []

    for key, value in parameters.items():
        current_path = f"{path}.{key}" if path else key

        if isinstance(value, str):
            # Check for N8N expression patterns
            if "{{" in value and "}}" in value:
                expressions.append({
                    "path": current_path,
                    "expression": value,
                    "type": "template"
                })
            elif value.startswith("="):
                expressions.append({
                    "path": current_path,
                    "expression": value[1:],  # Remove leading =
                    "type": "expression"
                })
        elif isinstance(value, dict):
            expressions.extend(extract_expressions(value, current_path))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    expressions.extend(extract_expressions(item, f"{current_path}[{i}]"))

    return expressions


def generate_mermaid(workflow: N8NWorkflow) -> str:
    """Generate a Mermaid flowchart from the workflow."""
    lines = ["flowchart TD"]

    # Node name sanitization for Mermaid
    def sanitize(name: str) -> str:
        return name.replace(" ", "_").replace("-", "_").replace(".", "_")

    # Add nodes
    for node in workflow.nodes:
        safe_name = sanitize(node.name)
        display_name = node.name

        # Different shapes for different node types
        if node.is_trigger:
            lines.append(f'    {safe_name}(("{display_name}"))')
        elif "if" in node.type.lower():
            lines.append(f'    {safe_name}{{{display_name}}}')
        else:
            lines.append(f'    {safe_name}["{display_name}"]')

    # Add connections
    for node in workflow.nodes:
        safe_source = sanitize(node.name)
        for target_name in node.outgoing:
            safe_target = sanitize(target_name)
            lines.append(f'    {safe_source} --> {safe_target}')

    return "\n".join(lines)


def workflow_to_dict(workflow: N8NWorkflow) -> dict:
    """Convert workflow to serializable dictionary."""
    return {
        "name": workflow.name,
        "id": workflow.id,
        "trigger": {
            "name": workflow.trigger_node.name,
            "type": workflow.trigger_node.type,
            "parameters": workflow.trigger_node.parameters,
        } if workflow.trigger_node else None,
        "nodes": [
            {
                "name": node.name,
                "type": node.type,
                "type_version": node.type_version,
                "parameters": node.parameters,
                "credentials": node.credentials,
                "is_trigger": node.is_trigger,
                "incoming": node.incoming,
                "outgoing": node.outgoing,
                "expressions": extract_expressions(node.parameters),
            }
            for node in workflow.nodes
        ],
        "execution_order": workflow.execution_order,
        "mermaid": generate_mermaid(workflow),
        "settings": workflow.settings,
    }


def format_summary(workflow: N8NWorkflow) -> str:
    """Generate a human-readable summary of the workflow."""
    lines = [
        f"# Workflow: {workflow.name}",
        "",
        "## Trigger",
    ]

    if workflow.trigger_node:
        lines.extend([
            f"- Type: {workflow.trigger_node.type}",
            f"- Name: {workflow.trigger_node.name}",
        ])
    else:
        lines.append("- No trigger detected (manual execution only)")

    lines.extend([
        "",
        "## Nodes",
        f"Total: {len(workflow.nodes)}",
        "",
    ])

    for i, node_name in enumerate(workflow.execution_order, 1):
        node = next((n for n in workflow.nodes if n.name == node_name), None)
        if node:
            trigger_mark = " (TRIGGER)" if node.is_trigger else ""
            lines.append(f"{i}. **{node.name}**{trigger_mark}")
            lines.append(f"   - Type: `{node.type}`")

            expressions = extract_expressions(node.parameters)
            if expressions:
                lines.append(f"   - Expressions: {len(expressions)}")

    lines.extend([
        "",
        "## Flow Diagram",
        "```mermaid",
        generate_mermaid(workflow),
        "```",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Parse N8N workflow JSON exports"
    )
    parser.add_argument(
        "--input", "-i",
        help="Input JSON file (reads from stdin if not provided)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file (prints to stdout if not provided)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "summary"],
        default="summary",
        help="Output format (default: summary)"
    )

    args = parser.parse_args()

    # Read input
    if args.input:
        with open(args.input, "r") as f:
            workflow_json = json.load(f)
    else:
        workflow_json = json.load(sys.stdin)

    # Parse workflow
    workflow = parse_workflow(workflow_json)

    # Generate output
    if args.format == "json":
        output = json.dumps(workflow_to_dict(workflow), indent=2)
    else:
        output = format_summary(workflow)

    # Write output
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Output written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
