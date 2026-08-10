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

        print("=" * 80)
        print("STEP 1 - Downloading")
        print("=" * 80)

        html = self.downloader.download(url)

        print(f"Downloaded {len(html)} characters")

        print("=" * 80)
        print("STEP 2 - Extracting")
        print("=" * 80)

        text = self.extractor.extract(html)

        print(f"Extracted {len(text)} characters")

        print("=" * 80)
        print("STEP 3 - Cleaning")
        print("=" * 80)

        cleaned = self.cleaner.clean(text)

        print(f"Cleaned {len(cleaned)} characters")

        print("=" * 80)
        print("STEP 4 - Building Prompt")
        print("=" * 80)

        prompt = self.prompt_builder.build(cleaned)

        print(prompt[:1000])

        print("=" * 80)
        print("STEP 5 - Sending to GPT-5.6 Luna")
        print("=" * 80)

        response = self.ai.analyze(prompt)

        print(response)

        print("=" * 80)
        print("STEP 6 - Validating")
        print("=" * 80)

        data = self.validator.validate(response)

        print("=" * 80)
        print("STEP 7 - Saving Lead")
        print("=" * 80)

        data["source_url"] = url

        lead = self.repository.create(data)

        print("Saved Lead ID:", lead.id)

        return lead