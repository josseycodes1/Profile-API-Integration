from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


class Stage3AuthEndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    @patch.dict("os.environ", {"GITHUB_CLIENT_ID": "test-client-id"})
    def test_github_auth_redirect_sets_secure_pkce_cookies(self):
        response = self.client.get("/auth/github", HTTP_ORIGIN="http://localhost:3000")

        self.assertEqual(response.status_code, 302)
        self.assertIn("https://github.com/login/oauth/authorize", response["Location"])
        self.assertIn("state=", response["Location"])
        self.assertIn("code_challenge=", response["Location"])
        self.assertIn("code_challenge_method=S256", response["Location"])
        self.assertTrue(response.cookies["oauth_state"]["httponly"])
        self.assertTrue(response.cookies["code_verifier"]["httponly"])

    @patch.dict("os.environ", {"GITHUB_CLIENT_ID": "test-client-id"})
    def test_github_auth_is_rate_limited(self):
        for _ in range(10):
            response = self.client.get("/auth/github", HTTP_ORIGIN="http://localhost:3000")
            self.assertEqual(response.status_code, 302)

        response = self.client.get("/auth/github", HTTP_ORIGIN="http://localhost:3000")
        self.assertEqual(response.status_code, 429)

    def test_refresh_rotates_refresh_token(self):
        user = User.objects.create_user(email="analyst@example.com", password="pass")
        refresh = RefreshToken.for_user(user)

        response = self.client.post(
            "/auth/refresh",
            {"refresh_token": str(refresh)},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "success")
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertNotEqual(response.data["refresh_token"], str(refresh))

    def test_logout_requires_post(self):
        response = self.client.get("/auth/logout")
        self.assertEqual(response.status_code, 405)

    def test_users_me_returns_authenticated_user(self):
        user = User.objects.create_user(
            email="admin@example.com",
            password="pass",
            role="admin",
            github_id="123",
        )
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = self.client.get("/api/users/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["email"], "admin@example.com")
        self.assertEqual(response.data["data"]["role"], "admin")
