from pathlib import Path


class PromptLoader:
    """
    Loads Markdown prompt templates from disk.
    """

    BASE_PATH = Path(__file__).parent.parent

    def load(self, relative_path: str) -> str:

        file_path = self.BASE_PATH / relative_path

        with open(
            file_path,
            encoding="utf-8",
        ) as file:

            return file.read()