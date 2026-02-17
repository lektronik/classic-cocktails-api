from rest_framework.test import APITestCase
from django.urls import reverse
from drinks.models import Drink, Category, Tag, GlassType, RecipeIngredient, DrinkIngredientsList
from drinks.serializers import DrinkSerializer

class APITests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Classic")
        self.glass = GlassType.objects.create(name="Martini")
        self.tag = Tag.objects.create(name="Summer")
        self.ingredient = RecipeIngredient.objects.create(name="Gin")
        self.drink = Drink.objects.create(
            name="Martini",
            category=self.category,
            glass_type=self.glass,
            instructions="Stir with ice and strain."
        )
        self.drink.tags.add(self.tag)
        DrinkIngredientsList.objects.create(
            drink=self.drink,
            ingredient=self.ingredient,
            quantity_text="2 oz"
        )

    def test_home_view(self):
        response = self.client.get(reverse('api-root'))
        self.assertEqual(response.status_code, 200)

    def test_drink_list(self):
        response = self.client.get(reverse('cocktail-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.drink.name)

    def test_drink_detail(self):
        url = reverse('cocktail-detail', args=[self.drink.id]) # Assuming lookup is by ID or slug? View uses logic.
        # Let's check the serializer's URL generation logic or try safe name
        safe_name = self.drink.name
        url = reverse('cocktail-detail', args=[safe_name])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], self.drink.name)
        self.assertIn('Gin', response.data['ingredient_names'])

    def test_category_list(self):
        response = self.client.get(reverse('category-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.category.name)

    def test_tag_list(self):
        response = self.client.get(reverse('tag-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.tag.name)

    def test_recipe_ingredient_list(self):
        response = self.client.get(reverse('recipe_ingredient-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ingredient.name)
