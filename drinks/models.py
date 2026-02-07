from __future__ import annotations

from django.db import models
from django.db.models.signals import post_migrate
from django.dispatch import receiver


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)


    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class GlassType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self) -> str:
        return self.name
    class Meta:
        ordering = ['name']


class RecipeIngredient(models.Model):
    name = models.CharField(max_length=200, unique=True)
    details = models.CharField(max_length=200, blank=True, default='')

    def __str__(self) -> str:
        return self.name
    class Meta:
        ordering = ['name']


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self) -> str:
        return self.name
    class Meta:
        ordering = ['name']


class PreparationMethod(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self) -> str:
        return self.name
    class Meta:
        ordering = ['name']


class Unit(models.Model):
    name = models.CharField(max_length=50, unique=True)
    plural = models.CharField(max_length=50, blank=True, default='')

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ['name']

    def display_with_quantity(self, quantity) -> str:
        try:
            is_one = isinstance(quantity, int) and quantity == 1
        except Exception:
            is_one = False
        if is_one:
            return f"{quantity} {self.name}"
        plural = self.plural or (self.name + 's')
        return f"{quantity} {plural}"


class Drink(models.Model):
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='drinks/', null=True, blank=True)
    instructions = models.TextField(blank=True, default='')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    preparation_method = models.ManyToManyField(PreparationMethod, blank=True)
    garnish = models.ManyToManyField('drinks.RecipeIngredient', blank=True, related_name='garnish_for')

    glass_type = models.ForeignKey(GlassType, on_delete=models.SET_NULL, null=True, blank=True)

    is_shot = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name
    class Meta:
        ordering = ['name']


class DrinkIngredientsList(models.Model):
    drink = models.ForeignKey(Drink, on_delete=models.CASCADE, related_name='recipe_ingredients')
    ingredient = models.ForeignKey('drinks.RecipeIngredient', on_delete=models.CASCADE, related_query_name='drinkingredient')
    quantity = models.FloatField(null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True)
    quantity_text = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        verbose_name = 'Recipe ingredient'
        verbose_name_plural = 'Recipe ingredients'
        db_table = 'drinks_drinkingredient'
        ordering = ['id']

    def __str__(self) -> str:
        return f"{self.ingredient} for {self.drink}"


class Cocktail(Drink):
    class Meta:
        proxy = True
        verbose_name = 'Cocktail'
        verbose_name_plural = 'Cocktails'


class GarnishIngredient(RecipeIngredient):
    class Meta:
        proxy = True
        verbose_name = 'Garnish Ingredient'
        verbose_name_plural = 'Garnish Ingredients'


@receiver(post_migrate)
def create_default_categories(sender, **kwargs):
    if sender and getattr(sender, 'name', '') != 'drinks':
        return
    defaults = ['Cocktails Throughout History', 'Shots', 'My Recipes']
    for name in defaults:
        existing = Category.objects.filter(name__iexact=name).first()
        if existing:
            if existing.name != name:
                try:
                    existing.name = name
                    existing.save()
                except Exception:
                    pass
        else:
            Category.objects.create(name=name)
