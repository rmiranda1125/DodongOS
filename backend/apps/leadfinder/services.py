from apps.ai.ollama_client import OllamaClient

from .scraper import WebsiteScraper
from .prompts import build_website_prompt
from .parser import LeadParser


class LeadFinderService:

    def __init__(self):

        self.scraper = WebsiteScraper()
        self.ai = OllamaClient()
        self.parser = LeadParser()

    def analyze(self, url):

        text = self.scraper.scrape(url)

        prompt = build_website_prompt(text)

        response = self.ai.analyze(prompt)

        return self.parser.parse(response)