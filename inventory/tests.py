from django.test import TestCase
from django.urls import reverse

class BasicViewTests(TestCase):
    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_home_page_loads_or_redirects(self):
        response = self.client.get(reverse("home"))
        self.assertIn(response.status_code, [200, 302])
