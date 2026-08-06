from bs4 import BeautifulSoup


class HTMLExtractor:
    """
    Extracts readable text from HTML.
    """

    def extract(self, html: str) -> str:

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        # Remove unwanted elements
        for tag in soup(
            [
                "script",
                "style",
                "noscript",
                "svg",
                "header",
                "footer",
                "nav",
                "aside",
            ]
        ):
            tag.decompose()

        text = soup.get_text(
            separator="\n",
            strip=True,
        )

        return text