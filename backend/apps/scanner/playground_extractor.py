from apps.scanner.services.downloader import HTMLDownloader
from apps.scanner.services.extractor import HTMLExtractor

url = "https://example.com"

html = HTMLDownloader().download(url)

text = HTMLExtractor().extract(html)

print(text[:2000])