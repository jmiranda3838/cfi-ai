from dataclasses import dataclass, field
from typing import Any

from google.genai import types


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)

    def to_function_declaration(self) -> types.FunctionDeclaration:
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters_json_schema=self.input_schema,
        )


class BaseTool:
    name: str = ""
    mutating: bool = False

    def definition(self) -> ToolDefinition:
        raise NotImplementedError

    def execute(self, workspace, client=None, **kwargs) -> str:
        raise NotImplementedError
