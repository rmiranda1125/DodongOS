import re


class HTMLCleaner:
    """
    Cleans extracted webpage text before sending it to AI.
    """

    REMOVE_PHRASES = {
        "accept cookies",
        "cookie policy",
        "privacy policy",
        "terms of service",
        "copyright",
        "facebook",
        "instagram",
        "linkedin",
        "twitter",
        "youtube",
        "all rights reserved",
        "back to top",
    }

    MIN_LINE_LENGTH = 5

    def clean(self, text: str) -> str:

        cleaned_lines = []

        for line in text.splitlines():

            line = line.strip()

            if not line:
                continue

            lower = line.lower()

            if any(
                phrase in lower
                for phrase in self.REMOVE_PHRASES
            ):
                continue

            if len(line) < self.MIN_LINE_LENGTH:
                continue

            cleaned_lines.append(line)

        cleaned = "\n".join(cleaned_lines)

        cleaned = re.sub(
            r"\n{3,}",
            "\n\n",
            cleaned,
        )

        return cleaned.strip()