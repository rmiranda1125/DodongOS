from apps.ai.prompt_loader import PromptLoader


class LeadScannerPromptBuilder:

    PROMPT_FILE = (
        "scanner/prompts/"
        "lead_scanner_runtime_prompt.md"
    )

    def __init__(self):

        self.loader = PromptLoader()

    def build(self, cleaned_text: str) -> str:

        template = self.loader.load(
            self.PROMPT_FILE
        )

        return (
            template
            .replace(
                "{{CONTENT}}",
                cleaned_text,
            )
        )