from django.contrib.auth import get_user_model
from django.test import TestCase


class UserRegistrationTests(TestCase):
    def test_registration_creates_regular_user_and_allows_login(self):
        response = self.client.post(
            "/registro/",
            {
                "username": "estudiante_demo",
                "password1": "Dahlia-River-4092!",
                "password2": "Dahlia-River-4092!",
            },
        )

        self.assertRedirects(response, "/login/")
        user = get_user_model().objects.get(username="estudiante_demo")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        response = self.client.post(
            "/login/",
            {"username": "estudiante_demo", "password": "Dahlia-River-4092!"},
        )
        self.assertRedirects(response, "/academico/")
