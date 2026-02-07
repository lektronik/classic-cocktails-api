from django.contrib import admin
from django.utils.html import format_html, escape
from django.http import HttpResponse
from django.shortcuts import redirect
from django.db.models import Count
from django.db.models.functions import Lower
from django.urls import reverse as django_reverse, path

from drinks.models import (
    Drink,
    Tag,
    Category,
    PreparationMethod,
    Unit,
    GlassType,
    GarnishIngredient,
    RecipeIngredient,
    Cocktail,
)


class IngredientListFilter(admin.SimpleListFilter):
    title = 'ingredient'
    parameter_name = 'ingredient'

    def lookups(self, request, model_admin):
        qs = RecipeIngredient.objects.order_by('name')
        return [(str(i.pk), i.name) for i in qs]

    def queryset(self, request, queryset):
        val = self.value()
        if val:
            return queryset.filter(recipe_ingredients__ingredient__pk=val).distinct()
        return queryset


class DrinkIngredientsList(admin.ModelAdmin):
    list_display = ('name', 'category', 'glass_type', 'is_shot')
    inlines = []
    list_filter = (
        'glass_type',
        'is_shot',
        'category',
        IngredientListFilter,
        'tags',
        'preparation_method',
    )
    search_fields = ('name',)
    filter_horizontal = ('tags', 'preparation_method', 'garnish')
    autocomplete_fields = ('glass_type',)
    ordering = ('name',)

    actions = ['mark_as_shot', 'unmark_as_shot']


    def mark_as_shot(self, request, queryset):
        updated = queryset.update(is_shot=True)
        self.message_user(request, f"Marked {updated} drink(s) as shots.")
    mark_as_shot.short_description = 'Mark selected drinks as Shots'

    def unmark_as_shot(self, request, queryset):
        updated = queryset.update(is_shot=False)
        self.message_user(request, f"Cleared is_shot on {updated} drink(s).")
    unmark_as_shot.short_description = 'Unmark selected drinks as Shots'

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'garnish':
            kwargs['queryset'] = GarnishIngredient.objects.filter(garnish_for__isnull=False).distinct().order_by('name')
        return super().formfield_for_manytomany(db_field, request, **kwargs)


def admin_popup_dismiss_js(obj_id: str, obj_repr: str) -> HttpResponse:
    js = (
        '<script>'
        '(function(){var op=window.opener||window.parent;'
        'if(!op){window.close();return;}try{'
        'if(op.dismissAddRelatedObjectPopup){op.dismissAddRelatedObjectPopup(window,"%s","%s");}'
        'else if(op.dismissAddAnotherPopup){op.dismissAddAnotherPopup(window,"%s","%s");}'
        'else{try{op.location&&op.location.reload();}catch(e){} }'
        '}catch(e){}window.close();})();</script>'
    ) % (obj_id, obj_repr, obj_id, obj_repr)
    return HttpResponse(js)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by(Lower('name'))

class DrinkIngredientAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'drink', 'details', 'unit', 'quantity_text')
    list_filter = ('unit', 'drink')
    search_fields = ('ingredient__name', 'drink__name')
    autocomplete_fields = ('ingredient', 'drink')
    show_in_index = False
    ordering = ('ingredient__name',)

    def promote_to_garnish(self, request, queryset):

        promoted = 0
        removed = 0
        for di in queryset.select_related('drink', 'ingredient'):
            drink = di.drink
            ingr = di.ingredient
            if ingr and not drink.garnish.filter(pk=ingr.pk).exists():
                drink.garnish.add(ingr)
                promoted += 1
            try:
                di.delete()
                removed += 1
            except Exception:
                pass
        self.message_user(request, f"Promoted {promoted} garnish(s) and removed {removed} drink row(s).")
    promote_to_garnish.short_description = 'Promote selected recipe ingredients to Garnish'

    actions = ['promote_to_garnish']

    def details(self, obj):
        return obj.quantity
    details.short_description = 'Details'

try:
    admin.site.unregister(Drink)
except Exception:
    pass

try:
    admin.site.unregister(Cocktail)
except Exception:
    pass


class CocktailAdmin(DrinkIngredientsList):
    list_display = ('name', 'category', 'api_link')

    def api_link(self, obj):
        safe = (obj.name or '').replace(' ', '_')
        url = f"/api/All_Cocktails/{safe}/"
        return format_html('<a href="{}" target="_blank">{}</a>', url, url)
    api_link.short_description = 'API endpoint'
    ordering = ('name',)
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by(Lower('name'))


try:
    admin.site.register(Cocktail, CocktailAdmin)
except Exception:
    pass

class RecipeIngredientAdmin(admin.ModelAdmin):
    search_fields = ('name', 'details')
    inlines = []
    list_display = ('name', 'details', 'api_link', 'drinks_count')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by(Lower('name'))
    ordering = ('name',)

    def drinks_count(self, obj):
        return Drink.objects.filter(recipe_ingredients__ingredient=obj).distinct().count()
    drinks_count.short_description = 'Drinks Using'

    def api_link(self, obj):
        safe = obj.name.replace(' ', '_')
        url = f"/api/recipe_ingredients/{safe}/"
        return format_html('<a href="{}" target="_blank">{}</a>', url, url)
    api_link.short_description = 'API endpoint'

    def add_view(self, request, form_url='', extra_context=None):
        try:
            if request.method == 'POST':
                name = request.POST.get('name', '').strip()
                if name:
                    existing = RecipeIngredient.objects.filter(name__iexact=name).first()
                    if existing and (request.GET.get('_popup') or request.POST.get('_popup')):
                        obj_id = str(existing.pk)
                        obj_repr = escape(str(existing))

                        return admin_popup_dismiss_js(obj_id, obj_repr)
        except Exception:
            pass

        return super().add_view(request, form_url, extra_context)

admin.site.register(RecipeIngredient, RecipeIngredientAdmin)

@admin.register(GarnishIngredient)
class GarnishIngredientAdmin(admin.ModelAdmin):
    search_fields = ('name', 'details')
    list_display = ('name', 'details', 'api_link', 'drinks_count')
    fields = ('name', 'details')
    readonly_fields = ('api_link',)
    ordering = ('name',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(garnish_for__isnull=False).distinct().order_by('name')

    def api_link(self, obj):
        safe = obj.name.replace(' ', '_')
        url = f"/api/garnish_ingredients/{safe}/"
        return format_html('<a href="{}" target="_blank">{}</a>', url, url)
    api_link.short_description = 'API endpoint'

    def drinks_count(self, obj):
        return Drink.objects.filter(garnish=obj).distinct().count()
    drinks_count.short_description = 'Drinks Using'

    def add_view(self, request, form_url='', extra_context=None):
        try:
            if request.method == 'POST':
                name = request.POST.get('name', '').strip()
                if name:
                    existing = RecipeIngredient.objects.filter(name__iexact=name).first()
                    if existing and (request.GET.get('_popup') or request.POST.get('_popup')):
                        obj_id = str(existing.pk)
                        obj_repr = escape(str(existing))
                        return admin_popup_dismiss_js(obj_id, obj_repr)
        except Exception:
            pass

        return super().add_view(request, form_url, extra_context)


class DrinkRedirectAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        return {}
    search_fields = ('name',)

    def get_urls(self):
        urls = []
        try:
            if getattr(self, 'search_fields', None):
                app_label = self.model._meta.app_label
                model_name = self.model._meta.model_name
                name = f"{app_label}_{model_name}_autocomplete"
                urls = [path('autocomplete/', self.admin_site.admin_view(self.autocomplete_view), name=name)]
                try:
                    recipe_add_name = 'admin:drinks_recipeingredient_add'
                    dest_add_name = f"admin:{app_label}_{model_name}_add"
                    if recipe_add_name != dest_add_name:
                        def add_redirect_view(request):
                            return redirect(django_reverse(recipe_add_name))
                        urls.insert(0, path('add/', self.admin_site.admin_view(add_redirect_view), name=f"{app_label}_{model_name}_add"))
                except Exception:
                    pass
        except Exception:
            urls = []
        return urls

try:
    admin.site.register(Drink, DrinkRedirectAdmin)
except Exception:
    pass


class HiddenIngredientAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        return {}

    search_fields = ('name',)

    def get_urls(self):
        urls = super().get_urls()
        try:
            app_label = self.model._meta.app_label
            model_name = self.model._meta.model_name
            add_name = f"{app_label}_{model_name}_add"
            recipe_add_name = 'admin:drinks_recipeingredient_add'

            dest_add_name = f"admin:{app_label}_{model_name}_add"
            if recipe_add_name == dest_add_name:
                return urls

            def add_redirect_view(request):
                return redirect(django_reverse(recipe_add_name))

            from django.urls import path
            redirect_url = path('add/', self.admin_site.admin_view(add_redirect_view), name=add_name)
            return [redirect_url] + urls
        except Exception:
            return urls


@admin.register(Tag)


class TagAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    readonly_fields = ('api_link',)
    list_display = ('name', 'api_link', 'drinks_count')
    ordering = ('name',)
    def api_link(self, obj):
        safe = obj.name.replace(' ', '_')
        url = f"/api/tags/{safe}/"
        return format_html('<a href="{}" target="_blank">{}</a>', url, url)
    api_link.short_description = 'API endpoint'
    def drinks_count(self, obj):
        count = getattr(obj, 'drink_count', None)
        if count is None:
            from .models import Drink
            count = Drink.objects.filter(tags=obj).distinct().count()
        try:
            changelist = django_reverse('admin:drinks_drink_changelist')
            url = f"{changelist}?tags__id__exact={obj.pk}"
            return format_html('<a href="{}">{}</a>', url, count)
        except Exception:
            return count
    drinks_count.short_description = 'Drinks Using'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(drink_count=Count('drink', distinct=True)).order_by(Lower('name'))

admin.site.register(Category, CategoryAdmin)

@admin.register(PreparationMethod)


class PreparationMethodAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    readonly_fields = ('api_link',)
    list_display = ('name', 'api_link', 'drinks_count')
    ordering = ('name',)
    def api_link(self, obj):
        safe = obj.name.replace(' ', '_')
        url = f"/api/preparation_methods/{safe}/"
        return format_html('<a href="{}" target="_blank">{}</a>', url, url)
    api_link.short_description = 'API endpoint'
    def drinks_count(self, obj):
        count = getattr(obj, 'drink_count', None)
        if count is None:
            from .models import Drink
            count = Drink.objects.filter(preparation_method=obj).distinct().count()
        try:
            changelist = django_reverse('admin:drinks_drink_changelist')
            url = f"{changelist}?preparation_method__id__exact={obj.pk}"
            return format_html('<a href="{}">{}</a>', url, count)
        except Exception:
            return count
    drinks_count.short_description = 'Drinks Using'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(drink_count=Count('drink', distinct=True)).order_by(Lower('name'))

@admin.register(Unit)


class UnitAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    readonly_fields = ('api_link',)
    list_display = ('name', 'api_link')
    ordering = ('name',)
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by(Lower('name'))
    def api_link(self, obj):
        safe = obj.name.replace(' ', '_')
        url = f"/api/units/{safe}/"
        return format_html('<a href="{}" target="_blank">{}</a>', url, url)
    api_link.short_description = 'API endpoint'

@admin.register(GlassType)
class GlassTypeAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    ordering = ('name',)
    list_display = ('name', 'api_link', 'drinks_count')
    readonly_fields = ('api_link',)
    def api_link(self, obj):
        safe = obj.name.replace(' ', '_')
        url = f"/api/glass_types/{safe}/"
        return format_html('<a href="{}" target="_blank">{}</a>', url, url)
    api_link.short_description = 'API endpoint'
    def drinks_count(self, obj):
        count = getattr(obj, 'drink_count', None)
        if count is None:
            from .models import Drink
            count = Drink.objects.filter(glass_type=obj).distinct().count()
        try:
            changelist = django_reverse('admin:drinks_drink_changelist')
            url = f"{changelist}?glass_type__id__exact={obj.pk}"
            return format_html('<a href="{}">{}</a>', url, count)
        except Exception:
            return count
    drinks_count.short_description = 'Drinks Using'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(drink_count=Count('drink', distinct=True)).order_by(Lower('name'))
