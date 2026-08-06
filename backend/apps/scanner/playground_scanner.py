from apps.scanner.services.scanner import LeadScanner

url = "https://example.com"

scanner = LeadScanner()

result = scanner.scan(url)

print(result)