# junox/context_processors.py
import requests
from django.conf import settings


def api_version_info(request):
    """
    Fetches the version from FastAPI's OpenAPI metadata.
    Returns a dictionary available in all templates as {{ api_info }}.
    """

    url = f"{settings.API_ROOT}/openapi.json"
    
    try:
        # Short timeout (0.5s) so page loads aren't delayed if API is down
        response = requests.get(url, timeout=0.5)
        if response.status_code == 200:
            data = response.json()
            version = data.get('info', {}).get('version', '0.0.0')
            return {
                'api_info': {
                    'version': f"v{version}",
                    'title': data.get('info', {}).get('title', 'JunoX API'),
                    'status': 'online'
                }
            }
    except Exception:
        pass

    return {
        'api_info': {
            'version': "Offline",
            'title': 'JunoX API',
            'status': 'offline'
        }
    }