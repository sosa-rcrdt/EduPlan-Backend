import requests
import sys

BASE_URL = 'http://127.0.0.1:8000'
USERNAME = 'testuser'
PASSWORD = 'testpassword123'

def verify_jwt():
    # 1. Obtain Token
    print("1. Obtaining Token Pair...")
    response = requests.post(f'{BASE_URL}/token/', data={'username': USERNAME, 'password': PASSWORD})
    if response.status_code != 200:
        print(f"Failed to obtain token: {response.text}")
        return False
    
    tokens = response.json()
    access = tokens.get('access')
    refresh = tokens.get('refresh')
    
    if not access or not refresh:
        print("Failed to get access or refresh token.")
        return False
    print("   Success! Got access and refresh tokens.")

    # 2. Verify Access Token (Optional - if there was a protected endpoint)
    # For now, we assume if we got it, it works.

    # 3. Refresh Token
    print("2. Refreshing Token...")
    response = requests.post(f'{BASE_URL}/token/refresh/', data={'refresh': refresh})
    if response.status_code != 200:
        print(f"Failed to refresh token: {response.text}")
        return False
    
    new_tokens = response.json()
    new_access = new_tokens.get('access')
    # SimpleJWT might not rotate refresh token by default unless configured, but we configured it.
    new_refresh = new_tokens.get('refresh') 
    
    if not new_access:
        print("Failed to get new access token.")
        return False
    print("   Success! Refreshed token.")

    # 4. Blacklist Token (Logout)
    print("3. Blacklisting Token (Logout)...")
    token_to_blacklist = new_refresh if new_refresh else refresh
    # The Logout view expects 'refresh_token' in the body
    response = requests.post(f'{BASE_URL}/logout/', data={'refresh_token': token_to_blacklist}, headers={'Authorization': f'Bearer {new_access}'})
    
    if response.status_code != 200:
        print(f"Failed to blacklist token: {response.text}")
        return False
    print("   Success! Token blacklisted.")

    # 5. Verify Blacklist
    print("4. Verifying Blacklist (Trying to refresh with blacklisted token)...")
    response = requests.post(f'{BASE_URL}/token/refresh/', data={'refresh': token_to_blacklist})
    
    # Expecting 401 Unauthorized because the token is blacklisted
    if response.status_code == 401: 
        print("   Success! Blacklisted token was rejected.")
        return True
    else:
        print(f"Failed! Blacklisted token was NOT rejected. Status: {response.status_code}, Body: {response.text}")
        return False

if __name__ == "__main__":
    if verify_jwt():
        print("\nALL CHECKS PASSED")
        sys.exit(0)
    else:
        print("\nVERIFICATION FAILED")
        sys.exit(1)
