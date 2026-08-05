import requests
from bs4 import BeautifulSoup


class WebsiteScraper:

    def scrape(self, url: str) -> str:

        headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64)"
            )
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=20,
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        for tag in soup(
            [
                "script",
                "style",
                "noscript",
            ]
        ):
            tag.decompose()

        text = soup.get_text(
            separator=" ",
            strip=True,
        )

        return text[:10000]