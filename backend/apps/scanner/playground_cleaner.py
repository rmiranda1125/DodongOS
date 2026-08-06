from apps.scanner.services.downloader import HTMLDownloader
from apps.scanner.services.extractor import HTMLExtractor
from apps.scanner.services.cleaner import HTMLCleaner

url = "https://example.com"

html = HTMLDownloader().download(url)

text = HTMLExtractor().extract(html)

cleaned = HTMLCleaner().clean(text)

print(cleaned[:3000])