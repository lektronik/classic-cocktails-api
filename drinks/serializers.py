from rest_framework import serializers
from rest_framework.reverse import reverse
from django.urls import reverse as django_reverse
from urllib.parse import quote as urlquote
from drinks.models import (
    Drink,
    RecipeIngredient,
    DrinkIngredientsList,
    Tag,
    Category,
    PreparationMethod,
    Unit,
    GlassType,
)
import re
from fractions import Fraction
from django.http import Http404
from rest_framework.renderers import BrowsableAPIRenderer


class RemoveNoneFieldsMixin:

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not isinstance(data, dict):
            return data

        filtered = {k: v for k, v in data.items() if v is not None}

        try:
            request = self.context.get('request') if hasattr(self, 'context') else None
            renderer_format = None
            if request is not None:
                renderer_format = getattr(getattr(request, 'accepted_renderer', None), 'format', None)
            renderer = getattr(request, 'accepted_renderer', None)
            if isinstance(renderer, BrowsableAPIRenderer) or renderer_format == 'html':
                try:
                    instr = filtered.get('instructions')
                    if isinstance(instr, str) and instr.strip():

                        s = instr.replace('\n', ' ').strip()
                        s = re.sub(r'\s+', ' ', s)
                        filtered['instructions'] = s
                except Exception:
                    pass
        except Exception:
            pass

        return filtered


def _parse_measure(text: str):
    if not text:
        return (None, None)
    s = text.strip().replace('\u00bd', '1/2')
    if s.lower() in ('to taste', 'top', 'taste', 'dash', 'dashes', 'pinch'):
        return (None, s)
    m = re.match(r"^(?P<num>\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)\s*(?P<unit>.+)$", s)
    if not m:
        return (None, s)
    num = m.group('num')
    unit = m.group('unit').strip()
    try:
        if ' ' in num:
            whole, frac = num.split()
            quantity = int(whole) + float(Fraction(frac))
        elif '/' in num:
            quantity = float(Fraction(num))
        else:
            quantity = float(num)
            if quantity.is_integer():
                quantity = int(quantity)
    except Exception:
        return (None, s)
    return (quantity, unit)


def safe_name_from(text: str) -> str:
    if text is None:
        return ''
    return re.sub(r'[^0-9A-Za-z]+', '_', str(text)).strip('_')


def get_by_safe_name(model, safe_value):
    if safe_value is None:
        raise Http404
    lookup_name = str(safe_value).replace('_', ' ')
    try:
        obj = model.objects.filter(name__iexact=lookup_name).first()
        if obj:
            return obj
    except Exception:
        pass
    safe_normalized = re.sub(r'[^0-9A-Za-z]+', '_', str(safe_value)).strip('_').lower()
    try:
        for o in model.objects.all():
            name_sanitized = re.sub(r'[^0-9A-Za-z]+', '_', str(o.name)).strip('_').lower()
            if name_sanitized == safe_normalized:
                return o
    except Exception:
        pass
    raise Http404


class TagSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = Tag
        fields = ['name', 'url']

    def get_url(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        safe = safe_name_from(obj.name)
        try:
            if request is not None:
                return reverse('tag-detail', args=[safe], request=request)
        except Exception:
            pass
        try:
            return django_reverse('tag-detail', args=[safe])
        except Exception:
            return f"/api/tags/{safe}/"


class CategorySerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    name = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['name', 'url']

    def get_url(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        try:
            if request is not None:
                renderer = getattr(getattr(request, 'accepted_renderer', None), 'format', None)
                base = reverse('category-list', request=request)
                if renderer in ('html', 'api'):
                    safe = safe_name_from(obj.name)
                    try:
                        return reverse('category-detail', args=[safe], request=request)
                    except Exception:
                        return f"{base.rstrip('/')}/{safe}/"
                return f"{base}?name={urlquote(obj.name)}"
        except Exception:
            pass
        safe = safe_name_from(getattr(obj, 'name', '') or '')
        return f"/api/categories/{safe}/"

    def get_name(self, obj):
        try:
            n = str(getattr(obj, 'name', '')).strip()
            if n and n.lower() == 'cocktails throughout history':
                return 'Cocktails Throughout History'
            return n
        except Exception:
            return getattr(obj, 'name', '')


class EmbeddedCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name']


class EmbeddedTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['name']


class EmbeddedGlassTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlassType
        fields = ['name']


class EmbeddedPreparationMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreparationMethod
        fields = ['name']


class PreparationMethodSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = PreparationMethod
        fields = ['name', 'url']

    def get_url(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        safe = safe_name_from(obj.name)
        try:
            if request is not None:
                return reverse('preparationmethod-detail', args=[safe], request=request)
        except Exception:
            pass
        try:
            return django_reverse('preparationmethod-detail', args=[safe])
        except Exception:
            return f"/api/preparation_methods/{safe}/"


class RecipeIngredientSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = RecipeIngredient
        fields = ['name', 'url']

    def get_url(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        safe = safe_name_from(obj.name)
        try:
            if request is not None:
                return reverse('recipe_ingredient-detail', args=[safe], request=request)
        except Exception:
            pass
        try:
            return django_reverse('recipe_ingredient-detail', args=[safe])
        except Exception:
            return f"/api/recipe_ingredients/{safe}/"


class GarnishIngredientSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = RecipeIngredient
        fields = ['name', 'url']

    def get_url(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        try:
            if request is not None:
                safe = safe_name_from(obj.name)
                return reverse('garnish_ingredient-detail', args=[safe], request=request)
        except Exception:
            pass
        try:
            safe = obj.name.replace(' ', '_')
            return django_reverse('garnish_ingredient-detail', args=[safe])
        except Exception:
            return f"/api/garnish_ingredients/{obj.name.replace(' ', '_')}/"


class UnitSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = Unit
        fields = ['name', 'plural', 'url']

    def get_url(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        safe = safe_name_from(obj.name)
        try:
            if request is not None:
                return reverse('unit-detail', args=[safe], request=request)
        except Exception:
            pass
        try:
            return django_reverse('unit-detail', args=[safe])
        except Exception:
            return f"/api/units/{safe}/"


class GlassTypeSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = GlassType
        fields = ['name', 'url']

    def get_url(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        safe = safe_name_from(obj.name)
        try:
            if request is not None:
                return reverse('glasstype-detail', args=[safe], request=request)
        except Exception:
            pass
        try:
            return django_reverse('glasstype-detail', args=[safe])
        except Exception:
            return f"/api/glass_types/{safe}/"


class DrinkIngredientSerializer(serializers.ModelSerializer):
    ingredient = RecipeIngredientSerializer(read_only=True)
    unit = UnitSerializer(read_only=True)

    class Meta:
        model = DrinkIngredientsList
        fields = ['ingredient', 'quantity', 'unit', 'quantity_text']

    def to_representation(self, instance):
        name = None
        if instance.ingredient:
            try:
                name = instance.ingredient.name
            except Exception:
                name = str(instance.ingredient)

        qty = instance.quantity
        unit_obj = instance.unit
        qty_text = (instance.quantity_text or '').strip()

        if (qty is None or (unit_obj is None and not qty_text)) and qty_text:
            parsed_qty, parsed_unit = _parse_measure(qty_text)
            if parsed_qty is not None:
                qty = parsed_qty
            if parsed_unit and not unit_obj:
                try:
                    unit_obj = Unit.objects.filter(name__iexact=parsed_unit).first()
                except Exception:
                    unit_obj = None

        if qty is not None:
            try:
                qty_str = format(float(qty), 'g')
            except Exception:
                qty_str = str(qty)
            unit_name = ''
            try:
                if unit_obj and getattr(unit_obj, 'name', None):
                    unit_name = unit_obj.name.strip()
            except Exception:
                unit_name = ''

            if unit_name:
                plural = getattr(unit_obj, 'plural', None) if unit_obj is not None else None
                try:
                    is_one = float(qty) == 1
                except Exception:
                    is_one = False
                if plural and not is_one:
                    display_unit = plural
                else:
                    if not is_one:
                        if unit_name.endswith('ch') or unit_name.endswith('sh') or unit_name.endswith('x') or unit_name.endswith('s'):
                            display_unit = unit_name + 'es'
                        elif unit_name.endswith('y') and len(unit_name) > 1 and unit_name[-2] not in 'aeiou':
                            display_unit = unit_name[:-1] + 'ies'
                        else:
                            display_unit = unit_name + 's'
                    else:
                        display_unit = unit_name
                display = f"{qty_str} {display_unit}"
            else:
                display = qty_str
        else:
            display = qty_text or ''

        if name and display:
            return f"{name} {display}"
        if name:
            return name
        return display


class DrinkSerializer(RemoveNoneFieldsMixin, serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    preparation_method = serializers.SerializerMethodField()
    glass_type = serializers.SerializerMethodField()
    recipe_ingredients = DrinkIngredientSerializer(many=True, read_only=True)
    garnish_ingredients = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    ingredient_names = serializers.SerializerMethodField()

    class Meta:
        model = Drink
        fields = ['name', 'url', 'image_url', 'tags', 'preparation_method', 'glass_type', 'recipe_ingredients', 'garnish_ingredients', 'instructions', 'ingredient_names']

    def get_url(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        safe = safe_name_from(obj.name)
        try:
            if request is not None:
                return reverse('cocktail-detail', args=[safe], request=request)
        except Exception:
            pass
        try:
            return django_reverse('cocktail-detail', args=[safe])
        except Exception:
            return f"/api/All_Cocktails/{safe}/"

    def get_image_url(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        try:
            if obj.image and getattr(obj.image, 'url', None):
                if request is not None:
                    return request.build_absolute_uri(obj.image.url)
                return obj.image.url
        except Exception:
            pass
        return None

    def get_garnish_ingredients(self, obj):
        try:
            names = [g.name for g in obj.garnish.all().order_by('name')]
            return names
        except Exception:
            return []


    def get_tags(self, obj):
        return [t.name for t in obj.tags.all().order_by('name')]

    def get_preparation_method(self, obj):
        return [p.name for p in obj.preparation_method.all().order_by('name')]

    def get_glass_type(self, obj):
        try:
            if obj.glass_type:
                return obj.glass_type.name
        except Exception:
            return None
        return None

    def get_ingredient_names(self, obj):
        """Return a simple list of all unique ingredient names (recipe + garnish) without units."""
        names = set()

        for item in obj.recipe_ingredients.all():
            if item.ingredient:
                names.add(item.ingredient.name)

        for g in obj.garnish.all():
            names.add(g.name)
        return sorted(list(names))
