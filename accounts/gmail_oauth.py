import os
from django.conf import settings
from google_auth_oauthlib.flow import Flow

# Google requires HTTPS for OAuth redirects, except for localhost during
# development. This line allows http://127.0.0.1 to work while testing.
# NEVER let this be set to '1' in a real production deployment.
if settings.DEBUG:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def build_flow(state=None):
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        state=state,
    )

    flow.redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
    return flow