from django.conf import settings


def version(request):
    """Expose the canonical Dodong OS version to every template."""
    return {"DODONG_VERSION": settings.DODONG_VERSION}
