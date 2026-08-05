from pprint import pprint

from apps.leadfinder.services import LeadFinderService

service = LeadFinderService()

result = service.analyze(
    "https://www.microsoft.com"
)

pprint(result)