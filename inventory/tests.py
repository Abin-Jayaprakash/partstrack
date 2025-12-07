from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from inventory.models import SparePart


class BasicViewTests(TestCase):
    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_home_page_loads_or_redirects(self):
        response = self.client.get(reverse("home"))
        self.assertIn(response.status_code, [200, 302])

    def test_dashboard_loads_or_redirects(self):
        response = self.client.get(reverse("dashboard"))
        self.assertIn(response.status_code, [200, 302])

    def test_spare_parts_list_requires_login(self):
        # anonymous should be redirected
        response = self.client.get(reverse("spare_parts_list"))
        self.assertEqual(response.status_code, 302)

    def test_add_part_creates_spare_part_as_admin(self):
        admin = User.objects.create_user(
            username="admin",
            password="testpass123",
            is_staff=True,
        )
        self.client.login(username="admin", password="testpass123")

        response = self.client.post(
            reverse("add_part"),
            {
                "part_number": "P001",
                "part_name": "Brake Pad",
                "quantity": 10,
                "price": 100,
                "minimum_stock": 5,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(SparePart.objects.filter(part_number="P001").exists())

    def test_delete_part_removes_spare_part(self):
        admin = User.objects.create_user(
            username="admin2",
            password="testpass123",
            is_staff=True,
        )
        self.client.login(username="admin2", password="testpass123")

        part = SparePart.objects.create(
            part_number="P002",
            part_name="Oil Filter",
            quantity=5,
            price=50,
            minimum_stock=2,
        )

        response = self.client.post(
            reverse("delete_part", args=[part.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(SparePart.objects.filter(pk=part.pk).exists())

    def test_edit_part_updates_spare_part(self):
        admin = User.objects.create_user(
            username="admin3",
            password="testpass123",
            is_staff=True,
        )
        self.client.login(username="admin3", password="testpass123")

        part = SparePart.objects.create(
            part_number="P003",
            part_name="Old Name",
            quantity=5,
            price=50,
            minimum_stock=2,
        )

        response = self.client.post(
            reverse("edit_part", args=[part.pk]),
            {
                "part_number": "P003",
                "part_name": "New Name",
                "quantity": 5,
                "price": 50,
                "minimum_stock": 2,
            },
        )

        part.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(part.part_name, "New Name")

    def test_employee_add_part_creates_spare_part(self):
        emp = User.objects.create_user(
            username="emp",
            password="testpass123",
            is_staff=False,
        )
        self.client.login(username="emp", password="testpass123")

        response = self.client.post(
            reverse("employee_add_part"),
            {
                "part_number": "E001",
                "part_name": "Employee Part",
                "quantity": 3,
                "price": 30,
                "minimum_stock": 1,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(SparePart.objects.filter(part_number="E001").exists())

    def test_employee_edit_part_updates_spare_part(self):
        emp = User.objects.create_user(
            username="emp2",
            password="testpass123",
            is_staff=False,
        )
        self.client.login(username="emp2", password="testpass123")

        part = SparePart.objects.create(
            part_number="E002",
            part_name="Old Emp Name",
            quantity=4,
            price=40,
            minimum_stock=1,
        )

        response = self.client.post(
            reverse("employee_edit_part", args=[part.pk]),
            {
                "part_number": "E002",
                "part_name": "New Emp Name",
                "quantity": 4,
                "price": 40,
                "minimum_stock": 1,
            },
        )

        part.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(part.part_name, "New Emp Name")
