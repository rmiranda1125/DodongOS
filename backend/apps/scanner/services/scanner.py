from apps.scanner.services.downloader import HTMLDownloader
from apps.scanner.services.extractor import HTMLExtractor
from apps.scanner.services.cleaner import HTMLCleaner
from apps.scanner.services.prompt_builder import LeadScannerPromptBuilder
from apps.scanner.services.validator import AIResponseValidator
from apps.scanner.services.deduplicator import LeadDeduplicator
from apps.scanner.services.repository import LeadRepository

from apps.ai.providers.gpt_luna import GPTLunaProvider


class LeadScanner:

    def __init__(self):

        self.downloader = HTMLDownloader()

        self.extractor = HTMLExtractor()

        self.cleaner = HTMLCleaner()

        self.prompt_builder = LeadScannerPromptBuilder()

        self.ai = GPTLunaProvider()

        self.validator = AIResponseValidator()

        self.deduplicator = LeadDeduplicator()

        self.repository = LeadRepository()

    def scan(self, url: str):

        # Step 1 - Download the webpage
        html = self.downloader.download(url)

        # Step 2 - Extract readable text
        text = self.extractor.extract(html)

        # Step 3 - Clean the extracted text
        cleaned = self.cleaner.clean(text)

        # Step 4 - Build the AI prompt
        prompt = self.prompt_builder.build(cleaned)

        # Step 5 - Ask GPT-5.6 Luna
        response = self.ai.analyze(prompt)

        # Step 6 - Validate AI response
        data = self.validator.validate(response)

        # Step 7 - Store metadata
        data["source_url"] = url

        # If AI did not return these fields yet,
        # initialize them to keep the repository happy.
        data.setdefault("website", "")
        data.setdefault("recommended_services", [])
        data.setdefault("pain_points", [])

        # Step 8 - Check for duplicates
        duplicate = self.deduplicator.find_duplicate(data)

        if duplicate:
            return duplicate

        # Step 9 - Save new lead
        return self.repository.create(data)