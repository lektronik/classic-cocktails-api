
from rest_framework.routers import DefaultRouter
from django.urls import path, include, re_path
from .views import (
    DrinkViewSet,
    RecipeIngredientViewSet,
    GarnishIngredientViewSet,
    TagViewSet,
    CategoryViewSet,
    PreparationMethodViewSet,
    HomeView,
    AboutView,
    UnitViewSet,
    GlassTypeViewSet,
    ReimportView,
    GalleryView,
    ContactView,
)
from django.views.generic import TemplateView
from django.shortcuts import redirect

router = DefaultRouter()
router.register(r'All_Cocktails', DrinkViewSet, basename='cocktail')
router.register(r'recipe_ingredients', RecipeIngredientViewSet, basename='recipe_ingredient')
router.register(r'garnish_ingredients', GarnishIngredientViewSet, basename='garnish_ingredient')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'preparation_methods', PreparationMethodViewSet, basename='preparationmethod')
router.register(r'units', UnitViewSet, basename='unit')
router.register(r'glass_types', GlassTypeViewSet, basename='glasstype')

urlpatterns = [

    path('api/', include([
        path('', HomeView.as_view(), name='api-root'),
        path('about/', AboutView.as_view(), name='api-about'),
        path('contact/', ContactView.as_view(), name='api-contact'),
        path('admin/import/', ReimportView.as_view(), name='api-admin-import'),
        path('', include(router.urls)),
    ])),


    path('ingredients/', lambda req: redirect('/api/recipe_ingredients/', permanent=True)),
    path('ingredients/<str:name>/', lambda req, name: redirect(f'/api/recipe_ingredients/{name}/', permanent=True)),
    path('drinks/', lambda req: redirect('/api/All_Cocktails/', permanent=True)),
    path('drinks/<str:name>/', lambda req, name: redirect(f'/api/All_Cocktails/{name}/', permanent=True)),


]
