from datetime import datetime


def site_metadata(request):
    """Global template context: site branding info available everywhere."""
    return {
        'SITE_NAME': 'CloudDNA',
        'SITE_TAGLINE': 'AI-Powered Cloud-Native Digital Asset Intelligence Platform',
        'CURRENT_YEAR': datetime.now().year,
    }
