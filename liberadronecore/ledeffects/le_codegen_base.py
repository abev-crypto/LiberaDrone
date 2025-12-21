import re
from typing import Any, Dict, List

import bpy

from liberadronecore.ledeffects.le_nodecategory import LDLED_Node


def _sanitize_identifier(text: str) -> str:
    """Convert a node label/name into a safe identifier for generated code."""
    safe = re.sub(r"[^0-9a-zA-Z_]", "_", text or "")
    if not safe:
        safe = "node"
    if safe[0].isdigit():
        safe = f"n_{safe}"
    return safe


class LDLED_CodeNodeBase(LDLED_Node):
    """
    Base mixin for LED effect nodes that emit code instead of executing in-place.

    Subclasses should override `build_code` to return a code snippet string that
    implements the node's behavior, using provided input variable names.
    """

    codegen_hint: bpy.props.StringProperty(
        name="Code Hint",
        description="Optional hint shown in generated code comments",
        default="",
    )

    def codegen_id(self) -> str:
        """Stable identifier to use when emitting code for this node."""
        label = getattr(self, "label", "") or getattr(self, "name", "") or self.bl_idname
        return _sanitize_identifier(label)

    def code_inputs(self) -> List[str]:
        """Return input socket names used as variables in generated code."""
        if not hasattr(self, "inputs"):
            return []
        return [sock.name for sock in self.inputs]

    def code_outputs(self) -> List[str]:
        """Return output socket names produced by generated code."""
        if not hasattr(self, "outputs"):
            return []
        return [sock.name for sock in self.outputs]

    def build_code(self, inputs: Dict[str, str]) -> str:
        """
        Override in subclasses to return code implementing this node.

        `inputs` maps socket names to variable identifiers resolved upstream.
        """
        raise NotImplementedError("Subclasses must implement build_code()")

    def emit_code(self, inputs: Dict[str, str]) -> Dict[str, Any]:
        """Package code, metadata, and declared inputs/outputs for codegen pipeline."""
        snippet = self.build_code(inputs)
        return {
            "id": self.codegen_id(),
            "code": snippet,
            "inputs": self.code_inputs(),
            "outputs": self.code_outputs(),
            "meta": {"hint": self.codegen_hint} if self.codegen_hint else {},
        }
