
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
            options={
                'verbose_name': 'Category',
                'verbose_name_plural': 'Categories',
            },
        ),
        migrations.CreateModel(
            name='GlassType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='PreparationMethod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='RecipeIngredient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
                ('details', models.CharField(blank=True, default='', max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Unit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('plural', models.CharField(blank=True, default='', max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Drink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('image', models.ImageField(blank=True, null=True, upload_to='drinks/')),
                ('instructions', models.TextField(blank=True, default='')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('is_shot', models.BooleanField(default=False)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='drinks.category')),
                ('glass_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='drinks.glasstype')),
                ('preparation_method', models.ManyToManyField(blank=True, to='drinks.preparationmethod')),
                ('garnish', models.ManyToManyField(blank=True, related_name='garnish_for', to='drinks.recipeingredient')),
                ('tags', models.ManyToManyField(blank=True, to='drinks.tag')),
            ],
        ),
        migrations.CreateModel(
            name='Cocktail',
            fields=[
            ],
            options={
                'verbose_name': 'Cocktail',
                'verbose_name_plural': 'Cocktails',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('drinks.drink',),
        ),
        migrations.CreateModel(
            name='GarnishIngredient',
            fields=[
            ],
            options={
                'verbose_name': 'Garnish Ingredient',
                'verbose_name_plural': 'Garnish Ingredients',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('drinks.recipeingredient',),
        ),
        migrations.CreateModel(
            name='DrinkIngredient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.FloatField(blank=True, null=True)),
                ('quantity_text', models.CharField(blank=True, default='', max_length=100)),
                ('drink', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipe_ingredients', to='drinks.drink')),
                ('ingredient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='drinks.recipeingredient')),
                ('unit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='drinks.unit')),
            ],
            options={
                'verbose_name': 'Drink Ingredient',
                'verbose_name_plural': 'Drink Ingredients',
                'ordering': ['id'],
            },
        ),
    ]
