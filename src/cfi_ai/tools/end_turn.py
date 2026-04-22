from cfi_ai.tools.base import BaseTool, ToolDefinition


class EndTurnTool(BaseTool):
    name = "end_turn"
    mutating = False

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="end_turn",
            description=(
                "Signal that your turn is complete and the user should review "
                "your work or respond. Call this when you have finished all "
                "work and want to hand control back. You may call it alone, "
                "or alongside the final tool calls of this turn — in either "
                "case the turn ends once those calls complete. You may also "
                "include text alongside this call."
            ),
            input_schema={"type": "object", "properties": {}},
        )

    def execute(self, workspace, client=None, **kwargs) -> str:
        return "Turn complete."
