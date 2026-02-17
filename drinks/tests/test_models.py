from django.test import TestCase
from drinks.models import (
    Category, GlassType, RecipeIngredient, Tag, PreparationMethod, Unit, Drink, DrinkIngredientsList
)

class ModelTests(TestCase):
    def test_category_str(self):
        category = Category.objects.create(name="Test Category")
        self.assertEqual(str(category), "Test Category")

    def test_glasstype_str(self):
        glass = GlassType.objects.create(name="Highball")
        self.assertEqual(str(glass), "Highball")

    def test_recipe_ingredient_str(self):
        ingredient = RecipeIngredient.objects.create(name="Rum")
        self.assertEqual(str(ingredient), "Rum")

    def test_tag_str(self):
        tag = Tag.objects.create(name="Summer")
        self.assertEqual(str(tag), "Summer")

    def test_preparation_method_str(self):
        method = PreparationMethod.objects.create(name="Shaken")
        self.assertEqual(str(method), "Shaken")

    def test_unit_str(self):
        unit = Unit.objects.create(name="oz")
        self.assertEqual(str(unit), "oz")

    def test_unit_display_with_quantity(self):
        unit = Unit.objects.create(name="slice", plural="slices")
        self.assertEqual(unit.display_with_quantity(1), "1 slice")
        self.assertEqual(unit.display_with_quantity(2), "2 slices")
        self.assertEqual(unit.display_with_quantity(1.5), "1.5 slices")

        unit_no_plural = Unit.objects.create(name="dash")
        self.assertEqual(unit_no_plural.display_with_quantity(2), "2 dashs") # Default behavior

    def test_drink_str(self):
        drink = Drink.objects.create(name="Mojito")
        self.assertEqual(str(drink), "Mojito")

    def test_drink_ingredients_list_str(self):
        drink = Drink.objects.create(name="Mojito")
        ingredient = RecipeIngredient.objects.create(name="Mint")
        item = DrinkIngredientsList.objects.create(drink=drink, ingredient=ingredient)
        self.assertEqual(str(item), "Mint for Mojito")

    def test_create_default_categories(self):
        # Default categories are created post-migrate
        self.assertTrue(Category.objects.filter(name="Cocktails Throughout History").exists())
        self.assertTrue(Category.objects.filter(name="Shots").exists())
        self.assertTrue(Category.objects.filter(name="My Recipes").exists())
