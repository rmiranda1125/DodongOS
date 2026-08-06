from apps.scanner.services.downloader import HTMLDownloader

url = "https://example.com"

downloader = HTMLDownloader()

html = downloader.download(url)

print(html[:1000])