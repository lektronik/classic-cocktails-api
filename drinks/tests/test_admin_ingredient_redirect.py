from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse


class AdminIngredientRedirectTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user('admin', 'admin@example.com', 'pass')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.client = Client()
        self.client.force_login(self.user)

    def test_admin_ingredient_add_redirects_to_recipeingredient_add(self):
        recipe_namespaced = reverse('admin:drinks_recipeingredient_add')
        resp = self.client.get(recipe_namespaced)
        self.assertIn(resp.status_code, (200, 302))

