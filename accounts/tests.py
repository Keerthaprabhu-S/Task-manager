from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase

PW = "Str0ngPass!9"

class AuthTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_register_sets_httponly_cookie_and_me_works(self):
        r = self.client.post("/api/auth/register/", {"username": "alice", "email": "a@x.com", "password": PW}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.cookies["access_token"]["httponly"])
        self.assertEqual(self.client.get("/api/auth/me/").data["username"], "alice")

    def test_duplicate_email_and_weak_password_rejected(self):
        self.client.post("/api/auth/register/", {"username": "alice", "email": "a@x.com", "password": PW}, format="json")
        r = APIClient().post("/api/auth/register/", {"username": "bob", "email": "A@x.com", "password": PW}, format="json")
        self.assertEqual(r.status_code, 400)
        r = APIClient().post("/api/auth/register/", {"username": "bob", "email": "b@x.com", "password": "12345678"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("error", r.data)

    def test_login_logout_and_protected_route(self):
        self.client.post("/api/auth/register/", {"username": "alice", "email": "a@x.com", "password": PW}, format="json")
        c = APIClient()
        self.assertEqual(c.get("/api/tasks/").status_code, 401)
        self.assertEqual(c.post("/api/auth/login/", {"username": "alice", "password": "wrong"}, format="json").status_code, 401)
        self.assertEqual(c.post("/api/auth/login/", {"username": "alice", "password": PW}, format="json").status_code, 200)
        self.assertEqual(c.get("/api/tasks/").status_code, 200)
        self.assertEqual(c.post("/api/auth/logout/").status_code, 204)
        self.assertEqual(c.get("/api/tasks/").status_code, 401)
