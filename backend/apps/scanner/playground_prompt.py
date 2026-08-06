from apps.scanner.services.downloader import HTMLDownloader
from apps.scanner.services.extractor import HTMLExtractor
from apps.scanner.services.cleaner import HTMLCleaner
from apps.scanner.services.prompt_builder import LeadScannerPromptBuilder

url = "https://example.com"

html = HTMLDownloader().download(url)

text = HTMLExtractor().extract(html)

cleaned = HTMLCleaner().clean(text)

prompt = LeadScannerPromptBuilder().build(cleaned)

print(prompt)