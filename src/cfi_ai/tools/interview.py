from cfi_ai.tools.base import BaseTool, ToolDefinition


class InterviewTool(BaseTool):
    name = "interview"
    mutating = False

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Ask the user structured questions interactively. Questions are "
                "presented one at a time. Use this when you need information from "
                "the user before proceeding (e.g., client identifiers, dates, "
                "preferences, or data to paste). Each question can optionally "
                "include suggested answers the user can choose from, or allow "
                "multiline input for pasting text. You may send all your questions "
                "at once — they will be presented sequentially."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "questions": {
                        "type": "array",
                        "description": "List of questions to ask the user.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "Short identifier for this question (e.g., 'client_id', 'intake_date').",
                                },
                                "text": {
                                    "type": "string",
                                    "description": "The question to display to the user.",
                                },
                                "options": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Optional list of suggested answers. The user can pick one or type a custom answer.",
                                },
                                "multiline": {
                                    "type": "boolean",
                                    "description": "If true, allow multiline input (for pasting text blocks).",
                                },
                                "default": {
                                    "type": "string",
                                    "description": "Optional default value accepted on empty input.",
                                },
                            },
                            "required": ["id", "text"],
                        },
                    },
                },
                "required": ["questions"],
            },
        )

    def execute(self, workspace, client=None, **kwargs) -> str:
        return "Error: interview tool is handled by the agent loop."
