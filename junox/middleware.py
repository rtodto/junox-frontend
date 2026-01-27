# junox/middleware.py
import jwt
import datetime
import requests
from django.conf import settings

API_URL = settings.API_URL


REFRESH_TOKEN_EXPIRE_IN_LESS_THAN = 5 #this is in minutes

class TokenAutoRefreshMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        #print(f"--- Middleware running for path: {request.path} ---") # TEST 1
        # 1. Grab tokens from the session
        token = request.session.get('auth_token')
        refresh_token = request.session.get('refresh_token')

        #print(f"Token: {token}") # TEST 2
        #print(f"Refresh Token: {refresh_token}") # TEST 2
        # 2. If we have a token, check if it's "stale"
        if token and refresh_token:
            try:
                # Decode without verification (we just want to read the 'exp' field)
                decoded = jwt.decode(token, options={"verify_signature": False})
                exp_timestamp = decoded.get('exp')
                
                # Convert timestamp to a datetime object
                exp_time = datetime.datetime.fromtimestamp(exp_timestamp, datetime.timezone.utc)
                now = datetime.datetime.now(datetime.timezone.utc)
                
                # 3. CRITICAL LOGIC: If token expires in less than 5 minutes, refresh it!
                if exp_time - now < datetime.timedelta(minutes=REFRESH_TOKEN_EXPIRE_IN_LESS_THAN):
                    #print("DEBUG: Token is expiring soon. Refreshing...") # TEST 2
                    # Call your FastAPI refresh endpoint
                    refresh_url = API_URL + "/refresh" # Adjust to your API URL
                    res = requests.post(refresh_url, json={"refresh_token": refresh_token})
                    
                    if res.status_code == 200:
                        # 4. Success! Save the new Access Token into the session
                        new_access_token = res.json().get('access_token')
                        request.session['auth_token'] = new_access_token
                        #print("DEBUG: Token refreshed automatically by middleware.")
            
            except Exception as e:
                # If anything goes wrong (API down, invalid token), 
                # we just let the request continue and the views will handle the 401.
                print(f"DEBUG: Middleware refresh failed: {e}")

        # 5. Let the request proceed to the view
        return self.get_response(request)