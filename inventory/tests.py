from django.test import TestCase
from django.urls import reverse

class BasicViewTests(TestCase):
    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
