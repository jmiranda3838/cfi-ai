from cfi_ai.tools.base import BaseTool, ToolDefinition


class EndTurnTool(BaseTool):
    name = "end_turn"
    mutating = False

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="end_turn",
            description=(
                "Signal that your turn is complete and the user should review "
                "your work or respond. Call this as the only tool call when you "
                "have finished all work and want to hand control back. You may "
                "include text alongside this call. Do not combine with other "
                "tool calls in the same response."
            ),
            input_schema={"type": "object", "properties": {}},
        )

    def execute(self, workspace, client=None, **kwargs) -> str:
        return "Turn complete."
