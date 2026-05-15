import requests
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from typing import Dict, Any, Optional, Tuple
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()

class GoogleAuthentication(BaseAuthentication):
    def __init__(self):
        super().__init__()
        self.google_user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"

    def authenticate(self, request) -> tuple[None, dict[str, Any]] | None:
        token = self._get_token_from_request(request)
        if not token:
            return None
        try:
            google_user_data = self.get_google_info(token)
            return None, google_user_data
        except Exception as e:
            raise AuthenticationFailed(f"Google authentication failed: {str(e)}")

    @staticmethod
    def _get_token_from_request(request) -> Optional[str]:
        if hasattr(request, 'data') and 'token' in request.data:
            return request.data.get('token')
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]
        return None
    def get_google_info(self, token: str) -> Dict[str, Any]:
        headers = {'Authorization': f'Bearer {token}'}
        try:
            response = requests.get(self.google_user_info_url, headers=headers, timeout=10)
            response.raise_for_status()
            user_data = response.json()
            required_fields = ['email', 'given_name', 'family_name']
            missing_fields = [field for field in required_fields if not user_data.get(field)]
            if missing_fields:
                raise ValueError(f"Missing required fields from Google: {missing_fields}")
            if not user_data.get('verified_email', False):
                raise ValueError("Google account email is not verified")
            return user_data
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to validate Google token: {str(e)}")
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Error processing Google user data: {str(e)}")
