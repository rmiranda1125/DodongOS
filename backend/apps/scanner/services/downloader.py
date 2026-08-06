import requests


class HTMLDownloader:
    """
    Downloads the HTML content of a webpage.
    """

    DEFAULT_TIMEOUT = 30

    def download(self, url: str) -> str:
        response = requests.get(
            url,
            timeout=self.DEFAULT_TIMEOUT,
            headers={
                "User-Agent": (
                    "DodongOS Lead Scanner "
                    "(Educational Project)"
                )
            },
        )

        response.raise_for_status()

        return response.text