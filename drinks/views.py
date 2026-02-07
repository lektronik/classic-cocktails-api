from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response as DRFResponse

from django.shortcuts import get_object_or_404
from django.utils.safestring import mark_safe
from django.http import Http404
from django.urls import resolve, get_script_prefix
from django.db.models import Count, Case, When, Value, IntegerField

from rest_framework.reverse import reverse
from drinks.models import Drink, RecipeIngredient, Tag, Category, PreparationMethod, Unit, GlassType
from .serializers import (
    DrinkSerializer,
    RecipeIngredientSerializer,
    TagSerializer,
    CategorySerializer,
    PreparationMethodSerializer,
    UnitSerializer,
    GlassTypeSerializer,
    GarnishIngredientSerializer,
    safe_name_from as _safe_name_from,
    get_by_safe_name as _get_by_safe_name,
)

from urllib.parse import urlparse
import re
import random
import html
import json


class AdminAwarePagination(PageNumberPagination):
    def get_paginated_response(self, data):
        return DRFResponse({'results': data})


class PrettyNameMixin:

    pagination_class = AdminAwarePagination
    def get_view_name(self):
        try:
            action = getattr(self, 'action', None)
            kwargs = getattr(self, 'kwargs', {}) or {}

            pk = kwargs.get('pk') or kwargs.get('slug') or kwargs.get('name')

            if action == 'retrieve' or pk:
                if pk and not str(pk).isdigit():
                    lookup_name = str(pk).replace('_', ' ')
                    serializer = getattr(self, 'serializer_class', None)
                    try:
                        if serializer and hasattr(serializer, 'Meta') and hasattr(serializer.Meta, 'model'):
                            model = serializer.Meta.model
                            obj = model.objects.filter(name__iexact=lookup_name).first()
                            if obj:
                                return getattr(obj, 'name', str(obj))
                    except Exception:
                        pass

                try:
                    obj = self.get_object()
                    return getattr(obj, 'name', str(obj))
                except Exception:
                    pass
        except Exception:
            pass


        try:
            serializer = getattr(self, 'serializer_class', None)
            if serializer and hasattr(serializer, 'Meta') and hasattr(serializer.Meta, 'model'):
                model = serializer.Meta.model

                verbose = getattr(model._meta, 'verbose_name_plural', None) or getattr(model._meta, 'verbose_name', None)
                if verbose:
                    return str(verbose).title()
        except Exception:
            pass

        return super().get_view_name()


class CustomBrowsableAPIRenderer(BrowsableAPIRenderer):

    def get_context(self, data, accepted_media_type, renderer_context):
        context = super().get_context(data, accepted_media_type, renderer_context)

        if context and 'extra_actions' in context:
            context['extra_actions'] = None
        return context

    def get_description(self, view, nodes=None):
        description = super().get_description(view, nodes)


        try:
            drinks_path = reverse('cocktail-list')
            random_url = f"{drinks_path.rstrip('/')}/random/"
        except Exception:

            random_url = '/api/All_Cocktails/random/'

        injection = f'''
        <style>
            /* Hide OPTIONS button */
            .button-form[data-method="OPTIONS"] {{
                display: none !important;
            }}
            /* Hide Extra Actions dropdown */
            div.dropdown:has(#extra-actions-menu),
            button#extra-actions-menu {{
                display: none !important;
            }}
        </style>
        <script>
            (function() {{
                function injectButton() {{
                    var region = document.querySelector('.region[aria-label="request form"]');
                    if (region && !document.getElementById('random-recipe-btn')) {{
                        var randomBtn = document.createElement('a');
                        randomBtn.id = "random-recipe-btn";
                        randomBtn.href = "{random_url}";
                        randomBtn.className = "btn btn-primary js-tooltip";
                        randomBtn.style.fontWeight = "bold";
                        randomBtn.style.float = "right";
                        randomBtn.style.marginRight = "10px";
                        randomBtn.innerHTML = "Random Recipe";
                        randomBtn.title = "Get a random cocktail recipe";

                        region.insertBefore(randomBtn, region.firstChild);
                    }}
                }}
                if (document.readyState === "complete" || document.readyState === "interactive") {{
                    injectButton();
                }} else {{
                    document.addEventListener("DOMContentLoaded", injectButton);
                }}
            }})();
        </script>
        '''
        return mark_safe(injection + description) if description else mark_safe(injection)

    def get_breadcrumbs(self, request):

        crumbs = []
        try:
            url = request.path
            prefix = get_script_prefix().rstrip('/')
            url_path = url[len(prefix):]


            def recurse(u, out, seen):
                try:
                    view, args, kwargs = resolve(u)
                except Exception:
                    return
                cls = getattr(view, 'cls', None)
                initkwargs = getattr(view, 'initkwargs', {})
                if cls is not None:
                    if not seen or seen[-1] != view:
                        inst = cls(**initkwargs)
                        try:
                            inst.request = request
                        except Exception:
                            pass
                        try:
                            inst.args = args
                            inst.kwargs = kwargs
                        except Exception:
                            pass
                        name = inst.get_view_name()
                        out.insert(0, (name, u))
                        seen.append(view)

                if u == '':
                    return
                if u.endswith('/'):
                    recurse(u.rstrip('/'), out, seen)
                    return
                recurse(u[:u.rfind('/') + 1], out, seen)

            recurse(url_path, crumbs, [])
        except Exception:
            return super().get_breadcrumbs(request)

        try:
            api_root_full = reverse('api-root', request=request)
            api_root_path = urlparse(api_root_full).path
            if not crumbs or (len(crumbs) and crumbs[0][1] != api_root_path):
                view, args, kwargs = resolve(api_root_path)
                cls = getattr(view, 'cls', None)
                initkwargs = getattr(view, 'initkwargs', {})
                if cls is not None:
                    inst = cls(**initkwargs)
                    try:
                        inst.request = request
                    except Exception:
                        pass
                    try:
                        inst.args = args
                        inst.kwargs = kwargs
                    except Exception:
                        pass
                    name = inst.get_view_name()
                    crumbs.insert(0, (name, api_root_path))
        except Exception:
            pass

        try:
            try:
                cocktail_full = reverse('cocktail-list', request=request)
                cocktail_path = urlparse(cocktail_full).path
            except Exception:
                cocktail_path = '/api/All_Cocktails/'
            if request.path.rstrip('/') == cocktail_path.rstrip('/'):
                try:
                    api_root_full = reverse('api-root', request=request)
                    api_root_path = urlparse(api_root_full).path
                except Exception:
                    api_root_path = '/api/'
                return [('Home', api_root_path), ('All Cocktails', cocktail_path)]
        except Exception:
            pass


        try:
            resources = {
                'tags': 'tag-list',
                'ingredients': 'recipe_ingredient-list',
                'recipe_ingredients': 'recipe_ingredient-list',
                'garnish_ingredients': 'garnish_ingredient-list',
                'preparation_methods': 'preparationmethod-list',
                'units': 'unit-list',
                'glass_types': 'glasstype-list',
            }
            path = request.path
            for seg, route_name in resources.items():
                if f'/{seg}/' in path:
                    try:
                        list_full = reverse(route_name, request=request)
                        list_path = urlparse(list_full).path
                        present = any(c[1] == list_path for c in crumbs)
                        if not present:
                            view, args, kwargs = resolve(list_path)
                            cls = getattr(view, 'cls', None)
                            initkwargs = getattr(view, 'initkwargs', {})
                            if cls is not None:
                                inst = cls(**initkwargs)
                                try:
                                    inst.request = request
                                except Exception:
                                    pass
                                try:
                                    inst.args = args
                                    inst.kwargs = kwargs
                                except Exception:
                                    pass
                                name = inst.get_view_name()
                                insert_at = 1 if crumbs else 0
                                crumbs.insert(insert_at, (name, list_path))
                    except Exception:
                        pass
                    break
        except Exception:
            pass


        try:

            if '/drinks/' in request.path or '/All_Cocktails/' in request.path or '/Cocktails/' in request.path:
                seg = request.path.rstrip('/').split('/')[-1]
                if seg and not seg.isdigit():
                    try:
                        drink = _get_by_safe_name(Drink, seg)
                        cat = getattr(drink, 'category', None)
                        try:
                            categories_full = reverse('category-list', request=request)
                            categories_path = urlparse(categories_full).path
                        except Exception:
                            categories_path = None

                        if categories_path:
                            present = any(c[1] == categories_path for c in crumbs)
                            if not present:
                                try:
                                    view, args, kwargs = resolve(categories_path)
                                    cls = getattr(view, 'cls', None)
                                    initkwargs = getattr(view, 'initkwargs', {})
                                    if cls is not None:
                                        inst = cls(**initkwargs)
                                        try:
                                            inst.request = request
                                        except Exception:
                                            pass
                                        try:
                                            inst.args = args
                                            inst.kwargs = kwargs
                                        except Exception:
                                            pass
                                        name = inst.get_view_name()
                                        insert_at = 1 if crumbs else 0
                                        crumbs.insert(insert_at, (name, categories_path))
                                except Exception:
                                    pass

                        if cat:
                                    try:
                                        public = _safe_name_from(cat.name)
                                        cat_path = reverse('category-detail', args=[public], request=request)
                                        cat_path = urlparse(cat_path).path
                                        if not any(c[1] == cat_path for c in crumbs):
                                            idx = next((i for i, c in enumerate(crumbs) if c[1] == categories_path), None)
                                            insert_at = (idx + 1) if idx is not None else (1 if crumbs else 0)
                                            crumbs.insert(insert_at, (cat.name, cat_path))
                                    except Exception:
                                        pass
                    except Exception:
                            try:
                                public = _safe_name_from(cat.name)
                                cat_path = reverse('category-detail', args=[public], request=request)
                                cat_path = urlparse(cat_path).path
                                if not any(c[1] == cat_path for c in crumbs):
                                    idx = next((i for i, c in enumerate(crumbs) if c[1] == categories_path), None)
                                    insert_at = (idx + 1) if idx is not None else (1 if crumbs else 0)
                                    crumbs.insert(insert_at, (cat.name, cat_path))
                            except Exception:
                                pass
                    if not present:
                        try:
                            view, args, kwargs = resolve(categories_path)
                            cls = getattr(view, 'cls', None)
                            initkwargs = getattr(view, 'initkwargs', {})
                            if cls is not None:
                                inst = cls(**initkwargs)
                                try:
                                    inst.request = request
                                except Exception:
                                    pass
                                try:
                                    inst.args = args
                                    inst.kwargs = kwargs
                                except Exception:
                                    pass
                                name = inst.get_view_name()
                                insert_at = 1 if crumbs else 0
                                crumbs.insert(insert_at, (name, categories_path))
                        except Exception:
                            pass
        except Exception:
            pass

        try:
            cleaned = []
            prev_label = None
            for label, url in crumbs:
                lab = label if not hasattr(label, '__html__') else str(label)
                try:
                    if '/garnish_ingredients/' in url and lab.lower().strip() in ('ingredients', 'ingredient'):
                        lab = 'Garnish Ingredients'
                except Exception:
                    pass
                if prev_label is not None and str(lab) == str(prev_label):
                    try:
                        seg = url.rstrip('/').split('/')[-1]
                        if seg and not seg.isdigit():
                            pretty = seg.replace('_', ' ').replace('-', ' ').strip()
                            lab = pretty.title()
                    except Exception:
                        pass
                if prev_label is None or str(lab) != str(prev_label):
                    cleaned.append((lab, url))
                    prev_label = lab
            try:
                if cleaned:
                    last_label, last_url = cleaned[-1]
                    ll_norm = str(last_label).strip().lower()
                    if (('drink' in ll_norm or 'cocktail' in ll_norm) and 'list' in ll_norm) or ll_norm in ('drink list', 'drinks', 'cocktail list', 'cocktails'):
                        if last_url and ('/drinks/' in last_url or '/All_Cocktails/' in last_url or '/Cocktails/' in last_url):
                            seg = last_url.rstrip('/').split('/')[-1]
                            if seg and not seg.isdigit():
                                try:
                                    obj = _get_by_safe_name(Drink, seg)
                                    cleaned[-1] = (getattr(obj, 'name', seg), last_url)
                                except Exception:
                                    pass
            except Exception:
                pass
            try:
                path = request.path
                seg = path.rstrip('/').split('/')[-1]
                is_drink_detail = False
                if seg and not seg.isdigit() and ('/drinks/' in path or '/All_Cocktails/' in path or '/Cocktails/' in path):
                    is_drink_detail = True

                if is_drink_detail:
                    try:
                        obj = _get_by_safe_name(Drink, seg)
                        cat = getattr(obj, 'category', None)
                    except Exception:
                        obj = None
                        cat = None

                    parts = []
                    try:
                        api_root_full = reverse('api-root', request=request)
                        api_root_path = urlparse(api_root_full).path
                        view, args, kwargs = resolve(api_root_path)
                        cls = getattr(view, 'cls', None)
                        initkwargs = getattr(view, 'initkwargs', {})
                        if cls is not None:
                            inst = cls(**initkwargs)
                            try:
                                inst.request = request
                            except Exception:
                                pass
                            parts.append(str(inst.get_view_name()))
                    except Exception:
                        pass

                    try:
                        categories_full = reverse('category-list', request=request)
                        categories_path = urlparse(categories_full).path
                        view, args, kwargs = resolve(categories_path)
                        cls = getattr(view, 'cls', None)
                        initkwargs = getattr(view, 'initkwargs', {})
                        if cls is not None:
                            inst = cls(**initkwargs)
                            try:
                                inst.request = request
                            except Exception:
                                pass
                            parts.append(str(inst.get_view_name()))
                    except Exception:
                        pass

                        try:
                            if cat:
                                public = _safe_name_from(cat.name)
                                parts.append(str(getattr(cat, 'name', public)))
                            else:
                                if obj and getattr(obj, 'is_shot', False):
                                    parts.append('Shots')
                        except Exception:
                            pass

                    if obj:
                        parts.append(str(getattr(obj, 'name', seg)))

                    import re as _re
                    def _strip_tags(s):
                        return _re.sub(r'<[^>]+>', '', s)

                    clean_parts = [_strip_tags(str(p)).strip() for p in parts if p]
                    if clean_parts:
                        crumbs_out = []
                        try:
                            api_root_full = reverse('api-root', request=request)
                            api_root_path = urlparse(api_root_full).path
                            view, args, kwargs = resolve(api_root_path)
                            cls = getattr(view, 'cls', None)
                            initkwargs = getattr(view, 'initkwargs', {})
                            if cls is not None:
                                inst = cls(**initkwargs)
                                try:
                                    inst.request = request
                                except Exception:
                                    pass
                                try:
                                    inst.args = args
                                    inst.kwargs = kwargs
                                except Exception:
                                    pass
                                crumbs_out.append((inst.get_view_name(), api_root_path))
                        except Exception:
                            pass

                        try:
                            categories_full = reverse('category-list', request=request)
                            categories_path = urlparse(categories_full).path
                            view, args, kwargs = resolve(categories_path)
                            cls = getattr(view, 'cls', None)
                            initkwargs = getattr(view, 'initkwargs', {})
                            if cls is not None:
                                inst = cls(**initkwargs)
                                try:
                                    inst.request = request
                                except Exception:
                                    pass
                                try:
                                    inst.args = args
                                    inst.kwargs = kwargs
                                except Exception:
                                    pass
                                crumbs_out.append((inst.get_view_name(), categories_path))
                        except Exception:
                            pass

                        try:
                            if cat:
                                public = _safe_name_from(cat.name)
                                cat_path = reverse('category-detail', args=[public], request=request)
                                cat_path = urlparse(cat_path).path
                                crumbs_out.append((str(getattr(cat, 'name', public)), cat_path))
                        except Exception:
                            pass

                        try:
                            crumbs_out.append((str(getattr(obj, 'name', seg)), request.path))
                        except Exception:
                            crumbs_out.append((seg, request.path))

                        return crumbs_out

            except Exception:
                pass
            return cleaned
        except Exception:
            return crumbs


    def render(self, data, accepted_media_type=None, renderer_context=None):
        result = super().render(data, accepted_media_type, renderer_context)
        try:
            text = result.decode('utf-8') if isinstance(result, (bytes, bytearray)) else str(result)
            import re

            try:
                text = re.sub(r'(<div[^>]*class=["\'][^"\']*(?:request|response)-info[^"\']*["\'][\s\S]*?<pre[^>]*class=["\'])(prettyprint)(["\'][^>]*>)', r"\1\2 nocode\3", text, flags=re.IGNORECASE)
            except Exception:
                pass
            try:
                pre_url_re = re.compile(r'(&quot;)(?P<url>https?://[^&<\s]*/api/(?:drinks|Cocktails|All_Cocktails)/[A-Za-z0-9_\-]+/?)(?P<end>&quot;)', re.IGNORECASE)
                def _wrap_pre_url(m):
                    quote, url, end = m.group(1), m.group('url'), m.group('end')
                    return f'{quote}<a href="{url}" rel="nofollow">{url}</a>{end}'
                text = pre_url_re.sub(_wrap_pre_url, text)
            except Exception:
                pass
            try:
                import html, json

                def _apply_custom_formatting(src_text, key_name, fmt_type='flat_value_aligned'):


                    q_pat = r'(?:&quot;|\")'


                    prefix_pat = r'(?P<prefix>(?:^|\n)\s*|\s+)'

                    if 'array' in fmt_type:

                        pattern = re.compile(prefix_pat + r'(' + q_pat + re.escape(key_name) + q_pat + r'\s*:\s*\[)(?P<inside>.*?)(\])', re.S)
                    else:

                        pattern = re.compile(prefix_pat + r'(' + q_pat + re.escape(key_name) + q_pat + r'\s*:\s*)(?P<value>' + q_pat + r'(?:[^"\\]|\\.)*?' + q_pat + r')', re.S)

                    def _repl(m):
                        prefix_full = m.group('prefix') or ''
                        if '\n' in prefix_full:
                            newline_part = '\n'
                            indent_spaces = prefix_full.replace('\n', '')
                        else:
                            newline_part = ''
                            indent_spaces = prefix_full
                        base_indent_len = len(indent_spaces)

                        if 'array' in fmt_type:
                            inside = m.group('inside')
                            full_start = m.group(2)
                            full_end = m.group(4)


                            inside_unescaped = html.unescape(inside)
                            items = re.findall(r'(?:(?:\")|\"|\')(.*?)(?:(?:\")|\"|\')', inside_unescaped, re.S)
                            if not items:
                                raw = re.sub(r'\s+', ' ', inside_unescaped).strip()
                                if not raw: return m.group(0)
                                parts = [p.strip().strip('"\'') for p in raw.split(',') if p.strip()]
                                items = parts

                            cleaned = []
                            for it in items:
                                try:
                                    decoded = bytes(it, 'utf-8').decode('unicode_escape')
                                except Exception:
                                    decoded = it
                                decoded = decoded.replace('\n', ' ').replace('\r', ' ').strip()
                                cleaned.append(decoded)

                            if 'stack' in fmt_type:


                                header_text_last_line = full_start.split('\n')[-1]
                                header_visual_offset = base_indent_len + len(html.unescape(header_text_last_line))
                                line_prefix = ' ' * header_visual_offset


                                joined = (',\n' + line_prefix).join(json.dumps(s, ensure_ascii=False) for s in cleaned)


                                total_indent = 0
                                text_indent = 0
                                content_line = full_start + joined + full_end
                                span_inner_text = indent_spaces + content_line
                            else:

                                joined = ', '.join(json.dumps(s, ensure_ascii=False) for s in cleaned)
                                content_line = full_start + joined + full_end


                                header_text = full_start
                                header_visual_len = base_indent_len + len(header_text.split('\n')[-1])

                                total_indent = header_visual_len
                                text_indent = -total_indent
                                span_inner_text = indent_spaces + content_line
                        else:

                            key_part = m.group(2)
                            val_part = m.group(3)
                            content_line = key_part + val_part

                            if fmt_type == 'block_key_aligned':

                                total_indent = base_indent_len
                                text_indent = -total_indent
                                span_inner_text = indent_spaces + content_line
                            else:

                                header_visual_len = base_indent_len + len(key_part.split('\n')[-1])
                                if key_name == 'instructions':

                                    content_line = f'{full_start}<span class="instr-wrap">"{inside}"</span>{full_end}'
                                    total_indent = 0
                                    text_indent = 0
                                    span_inner_text = indent_spaces + content_line
                                else:
                                    total_indent = header_visual_len
                                    text_indent = -total_indent
                                    span_inner_text = indent_spaces + content_line
                        return f'{newline_part}<span style="display:inline-block; margin-left:{total_indent}ch; text-indent:{text_indent}ch;">{span_inner_text}</span>'

                    return pattern.sub(_repl, src_text)


                fields_to_format = [
                    ('tags', 'array_flat'),
                    ('preparation_method', 'array_flat'),
                    ('garnish_ingredients', 'array_flat'),
                    ('recipe_ingredients', 'array_stack'),
                    ('instructions', 'flat_value_aligned'),
                ]

                for key, ftype in fields_to_format:
                    text = _apply_custom_formatting(text, key, ftype)
            except Exception:
                pass

            try:
                text = re.sub(r'\{\s*(?:&quot;|")results(?:&quot;|")\s*:\s*(?P<inner>\[.*?\]|\{.*?\})\s*\}', lambda m: m.group('inner'), text, flags=re.S)
            except Exception:
                pass
            try:
                pre_pattern = re.compile(r'(<pre[^>]*class=["\"][^"\']*prettyprint[^"\']*["\"][^>]*>)(?P<content>.*?)(</pre>)', re.S | re.I)
                def _align_closing_bracket(m):
                    open_tag = m.group(1)
                    content = m.group('content')
                    close_tag = m.group(3)

                    content = re.sub(r"\n[ \t]+(?=\])", "\n", content)


                    content = re.sub(r'(\r?\n)\s*\r?\n', r'\1', content)
                    return open_tag + content + close_tag
                text = pre_pattern.sub(_align_closing_bracket, text)
            except Exception:
                pass
            try:
                def _sanitize_instructions(m):
                    prefix = m.group(1)
                    content = m.group('inside')

                    sanitized = content.replace('\\n', ' ').replace('\n', ' ')

                    sanitized = re.sub(r'([.!?)])\s*[—–-]\s*', r'\1 ', sanitized)
                    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
                    sanitized = re.sub(r',(?=\S)', ', ', sanitized)
                    sanitized = re.sub(r'\s+(?=[\.,;:\?!])', '', sanitized)
                    sanitized = sanitized.replace('"', '\\"')
                    return f"{prefix}{sanitized}{m.group(3)}"

                instr_pattern_html = re.compile(r'((?:&quot;|")instructions(?:&quot;|")\s*:\s*&quot;)(?P<inside>.*?)(\&quot;)', re.S)
                text = instr_pattern_html.sub(lambda m: _sanitize_instructions(m), text)

                instr_pattern = re.compile(r'((?:"|\')instructions(?:"|\')\s*:\s*")(?P<inside>.*?)(")', re.S)
            except Exception:
                instr_pattern = None

            try:
                if instr_pattern:
                    text = instr_pattern.sub(lambda m: _sanitize_instructions(m), text)
            except Exception:
                pass

            return text.encode('utf-8')
        except Exception:
            return result
class HomeView(APIView):
    renderer_classes = (CustomBrowsableAPIRenderer, JSONRenderer)
    def get(self, request, format=None):
        req = request


        try:
            drinks = reverse('cocktail-list', request=req)
        except Exception:
            drinks = '/api/All_Cocktails/'
        try:
            categories = reverse('category-list', request=req)
        except Exception:
            categories = '/api/categories/'
        try:
            tags = reverse('tag-list', request=req)
        except Exception:
            tags = '/api/tags/'
        try:

            ingredients = reverse('recipe_ingredient-list', request=req)
        except Exception:

            ingredients = '/api/recipe_ingredients/'

        try:
            recipe_ingredients = reverse('recipe_ingredient-list', request=req)
        except Exception:
            recipe_ingredients = '/api/recipe_ingredients/'

        try:
            garnish_ingredients = reverse('garnishingredient-list', request=req)
        except Exception:

            try:
                garnish_ingredients = reverse('garnish_ingredient-list', request=req)
            except Exception:
                garnish_ingredients = '/api/garnish_ingredients/'
        try:
            prep = reverse('preparationmethod-list', request=req)
        except Exception:
            prep = '/api/preparation-methods/'
        try:
            units = reverse('unit-list', request=req)
        except Exception:
            units = '/api/units/'


        endpoints_ordered = [
            ('Cocktails', drinks),
            ('categories', categories),
            ('tags', tags),
            ('recipe_ingredients', recipe_ingredients),
            ('garnish_ingredients', garnish_ingredients),
            ('preparation_methods', prep),
            ('glass_types', reverse('glasstype-list', request=req) if req is not None else '/api/glass_types/'),
            ('units', units),
        ]

        endpoints = {}
        for key, url in endpoints_ordered:
            endpoints[key] = request.build_absolute_uri(url) if req is not None else url

        payload = {
            'title': 'Cocktail Recipes API',
            'description': 'Welcome to Cocktail Recipes API',
            'endpoints': endpoints,
        }

        is_html = False
        try:
            renderer = getattr(request, 'accepted_renderer', None)
            if renderer and getattr(renderer, 'format', None) in ('html', 'api'):
                is_html = True
        except Exception:
            is_html = False

        accept = request.META.get('HTTP_ACCEPT', '') if request is not None else ''
        fmt = request.query_params.get('format') if request is not None else None
        if (accept and 'text/html' in accept) or (fmt and fmt in ('html', 'api')):
            is_html = True


        if is_html:

            display_payload = {
                'title': payload['title'],
                'description': payload['description'],
            }
            all_eps = dict(payload.get('endpoints', {}))
            preferred_order = [
                'categories',
                'tags',
                'preparation_methods',
                'glass_types',
                'recipe_ingredients',
                'garnish_ingredients',
                'units',
            ]
            endpoints_display = {}
            for key in preferred_order:
                if key in all_eps:
                    endpoints_display[key] = all_eps.pop(key)

            for k, v in payload.get('endpoints', {}).items():
                if k == 'Cocktails':
                    continue
                if k not in endpoints_display:
                    endpoints_display[k] = v

            display_payload['endpoints'] = endpoints_display
            return Response(display_payload)

        return Response(payload)

    def get_view_name(self):
        try:
            req = getattr(self, 'request', None)
            if req is not None:
                try:
                    api_root_full = reverse('api-root', request=req)
                    from urllib.parse import urlparse
                    api_root_path = urlparse(api_root_full).path
                except Exception:
                    api_root_path = None

                if api_root_path and req.path == api_root_path:
                    return 'Home'
                return mark_safe('<span style="color:#c00;">Home</span>')
        except Exception:
            pass

        return 'Home'

    def get_view_description(self, *args, **kwargs):
        req = kwargs.get('request') or getattr(self, 'request', None)
        if req is not None and getattr(req, 'accepted_renderer', None) is not None and req.accepted_renderer.format in ('html', 'api'):
            nav = build_nav_html(req)
            header = f'<div style="margin-top:8px;margin-bottom:10px;"><h2>{"Cocktail Recipes API"}</h2><p>{"Welcome to Cocktail Recipes API"}</p></div>'
            return mark_safe(nav + header)
        if req:
            return mark_safe(build_nav_html(req))
        return super().get_view_description(*args, **kwargs)


class AboutView(APIView):
    renderer_classes = (CustomBrowsableAPIRenderer, JSONRenderer)
    def get(self, request, format=None):
        return Response({'description': 'A read-only Cocktail Recipes API. Created by Aristotelis Aslanidis.'})

    def get_view_description(self, *args, **kwargs):
        req = kwargs.get('request') or getattr(self, 'request', None)
        if req:
            return mark_safe(build_nav_html(req))
        return super().get_view_description(*args, **kwargs)


def build_nav_html(request):
    req = request
    try:
        home = reverse('api-root', request=req)
    except Exception:
        home = '/api/'
    try:
        drinks_path = reverse('cocktail-list')
    except Exception:
        drinks_path = '/api/All_Cocktails/'
    try:
        if req is not None:
            drinks = req.build_absolute_uri(drinks_path)
        else:
            drinks = drinks_path
    except Exception:
        drinks = drinks_path
    try:
        categories = reverse('category-list', request=req)
    except Exception:
        categories = '/api/categories/'

    from .serializers import safe_name_from as _safe_name_from
    try:
        cocktails_history = reverse('category-detail', args=[_safe_name_from('Cocktails Throughout History')], request=req)
    except Exception:
        cocktails_history = f"{categories}?name={_safe_name_from('Cocktails Throughout History')}"
    try:
        shots_link = reverse('category-detail', args=[_safe_name_from('Shots')], request=req)
    except Exception:
        shots_link = f"{categories}?name={_safe_name_from('Shots')}"
    try:
        my_recipes = reverse('category-detail', args=[_safe_name_from('My Recipes')], request=req)
    except Exception:
        my_recipes = f"{categories}?name={_safe_name_from('My Recipes')}"
    try:
        about = reverse('api-about', request=req)
    except Exception:
        about = '/api/about/'

    try:
        random_recipe_link = reverse('cocktail-random')
    except Exception:
        random_recipe_link = f"{drinks.rstrip('/')}/random/"

    nav = f'''
    <div style="margin-bottom:10px;">
        <a class="btn" style="background:#f5f5f5;color:#333;border:1px solid #ddd;margin-right:8px;padding:6px 12px;text-decoration:none;" href="{home}">Home</a>
        <a class="btn btn-default" href="{drinks}" onclick="window.location.href=this.getAttribute('href');return false;" style="margin-right:8px;padding:6px 12px;text-decoration:none;">All Cocktails</a>
        <a class="btn btn-default" href="{cocktails_history}" style="margin-right:8px;padding:6px 12px;text-decoration:none;">Cocktails Throughout History</a>
        <a class="btn btn-default" href="{shots_link}" style="margin-right:8px;padding:6px 12px;text-decoration:none;">Shots</a>
        <a class="btn btn-default" href="{my_recipes}" style="margin-right:8px;padding:6px 12px;text-decoration:none;">My Recipes</a>
        <a class="btn btn-default" href="{about}" style="padding:6px 12px;text-decoration:none;">About</a>
    </div>
    '''
    return nav


class DrinkViewSet(PrettyNameMixin, viewsets.ModelViewSet):
    queryset = Drink.objects.all().order_by('name')
    serializer_class = DrinkSerializer
    renderer_classes = (CustomBrowsableAPIRenderer, JSONRenderer)
    lookup_field = 'name'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'instructions']
    ordering_fields = ['name', 'created']

    @action(detail=False, methods=['get'], name='Random Recipe', url_path='random')
    def random(self, request):
        """Return a random cocktail."""
        count = self.get_queryset().count()
        if count == 0:
            return Response({'detail': 'No cocktails found'}, status=status.HTTP_404_NOT_FOUND)
        random_index = random.randint(0, count - 1)
        obj = self.get_queryset()[random_index]
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    def get_view_name(self):
        action_name = getattr(self, 'action', None)
        path = getattr(self, 'request', None).path if hasattr(self, 'request') else ''


        if action_name == 'random' or path.rstrip('/').endswith('/random'):
            return 'Random Recipe'


        if action_name:
            action_method = getattr(self, action_name, None)
            if action_method and hasattr(action_method, 'kwargs') and 'name' in action_method.kwargs:
                return action_method.kwargs['name']


        try:
            kwargs = getattr(self, 'kwargs', {}) or {}
            pk = kwargs.get('pk') or kwargs.get('name') or kwargs.get('slug')
            if action_name == 'retrieve' or pk:
                if pk and not str(pk).isdigit():
                    try:
                        lookup_name = str(pk).replace('_', ' ')
                        obj = Drink.objects.filter(name__iexact=lookup_name).first()
                        if not obj:
                            obj = _get_by_safe_name(Drink, pk)
                        if obj:
                            return getattr(obj, 'name', str(obj))
                    except Exception:
                        pass
                try:
                    obj = self.get_object()
                    return getattr(obj, 'name', str(obj))
                except Exception:
                    pass
        except Exception:
            pass


        if action_name == 'list' or action_name is None:
            return 'All Cocktails'

        return super().get_view_name()


    def get_view_description(self, *args, **kwargs):
        req = kwargs.get('request') or getattr(self, 'request', None)
        if req is not None and getattr(req, 'accepted_renderer', None) is not None and req.accepted_renderer.format in ('html', 'api'):
            nav = build_nav_html(req)


            styles = '''
            <style>
                .instr-wrap {
                    display: inline-block;
                    white-space: pre-wrap !important;
                    padding-left: 1ch;
                    text-indent: -1ch;
                    vertical-align: top;
                    max-width: 100%;
                }
                pre.prettyprint {
                    white-space: pre-wrap !important;
                    word-break: break-word !important;
                }
            </style>
            '''
            nav = styles + nav
            try:
                if getattr(self, 'action', None) == 'retrieve' or getattr(self, 'kwargs', {}).get('name'):
                    lookup = getattr(self, 'kwargs', {}).get('name') or getattr(self, 'kwargs', {}).get('pk')
                    obj = None
                    if lookup and not str(lookup).isdigit():
                        try:
                            obj = _get_by_safe_name(Drink, lookup)
                        except Exception:
                            obj = None
                    if obj is None:
                        try:
                            obj = self.get_object()
                        except Exception:
                            obj = None
                    detail_parts = []
                    try:
                        img_field = getattr(obj, 'image', None)
                        if img_field and getattr(img_field, 'url', None):
                            img_url = req.build_absolute_uri(img_field.url)
                            detail_parts.append(
                                f'<div style="margin-bottom:10px; width:153px !important; height:230px !important; overflow:hidden; display:block !important; transform:none !important; -webkit-transform:none !important; zoom:1 !important;">'
                                f'<img src="{img_url}" width="153" height="230" '
                                f'style="width:153px !important; height:230px !important; box-sizing:border-box !important; object-fit:cover !important; max-width:153px !important; max-height:230px !important; border:1px solid #ddd !important; display:block !important; transform:none !important; -webkit-transform:none !important;"/>'
                                f'</div>'
                            )
                    except Exception:
                        pass
                    return mark_safe(nav + ''.join(detail_parts))
            except Exception:
                return mark_safe(nav)
            return mark_safe(nav)
        if req:
            return mark_safe(build_nav_html(req))

    def list(self, request, *args, **kwargs):
        """
        Extend list to support filtering by ingredient, tag, preparation, and shot flag via
        query params: `ingredient=<id>`, `tag=<id>`, `preparation=<id>`, and `is_shot=true|false`.
        """
        qs = self.get_queryset()
        def _parse_multi(key):
            vals = request.query_params.getlist(key)
            out = []
            for v in vals:
                if not v:
                    continue
                for part in v.split(','):
                    part = part.strip()
                    if not part:
                        continue
                    try:
                        ival = int(part)
                    except Exception:
                        raise ValueError(f"Invalid integer value for '{key}': {part}")
                    out.append(ival)
            return out

        try:
            ingredient_ids = _parse_multi('ingredient')
            tag_ids = _parse_multi('tag')
            prep_ids = _parse_multi('preparation')
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if ingredient_ids:
            qs = qs.filter(recipe_ingredients__ingredient__id__in=ingredient_ids).distinct()
        if tag_ids:
            qs = qs.filter(tags__id__in=tag_ids).distinct()

        category_name = request.query_params.get('category')
        if category_name:
            qs = qs.filter(category__name__iexact=category_name)
        if prep_ids:
            qs = qs.filter(preparation_method__id__in=prep_ids).distinct()

        is_shot_param = request.query_params.get('is_shot')
        if is_shot_param is not None:
            val = (is_shot_param or '').strip().lower()
            truthy = {'1', 'true', 't', 'yes', 'y'}
            falsey = {'0', 'false', 'f', 'no', 'n'}
            if val in truthy:
                qs = qs.filter(is_shot=True)
            elif val in falsey:
                qs = qs.filter(is_shot=False)
            else:
                return Response({'detail': "Invalid boolean for 'is_shot'. Use true/false or 1/0."}, status=status.HTTP_400_BAD_REQUEST)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response({'results': serializer.data})

    def retrieve(self, request, pk=None, *args, **kwargs):
        name = kwargs.get('name') or pk
        if name is None or str(name).isdigit():
            raise Http404
        if str(name).isdigit():
            obj = get_object_or_404(Drink, pk=name)
        else:
            obj = _get_by_safe_name(Drink, name)
        serializer = self.get_serializer(obj, context={"request": request})
        return Response(serializer.data)


class RecipeIngredientViewSet(PrettyNameMixin, viewsets.ModelViewSet):
    queryset = RecipeIngredient.objects.filter(drinkingredient__isnull=False).order_by('name').distinct()
    serializer_class = RecipeIngredientSerializer
    lookup_field = 'name'
    renderer_classes = (CustomBrowsableAPIRenderer, JSONRenderer)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']

    def get_view_name(self):
        if getattr(self, 'action', None) == 'list' or not getattr(self, 'kwargs', {}).get('name'):
            return 'Recipe Ingredients'
        try:
            obj = self.get_object()
            return getattr(obj, 'name', str(obj))
        except Exception:
            return super().get_view_name()

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(self.get_queryset(), many=True, context={"request": request})
        return Response({'results': serializer.data})

    def retrieve(self, request, pk=None, *args, **kwargs):
        name = kwargs.get('name') or pk
        if name is None:
            raise Http404
        if str(name).isdigit():
            ingredient = get_object_or_404(RecipeIngredient, pk=name)
        else:
            ingredient = _get_by_safe_name(RecipeIngredient, name)
        drinks_qs = Drink.objects.filter(recipe_ingredients__ingredient=ingredient).order_by('name').distinct()
        page = self.paginate_queryset(drinks_qs)
        if page is not None:
            drinks_ser = DrinkSerializer(page, many=True, context={"request": request, "suppress_category": True})
            return self.get_paginated_response(drinks_ser.data)
        drinks_ser = DrinkSerializer(drinks_qs, many=True, context={"request": request, "suppress_category": True})
        return Response({'results': drinks_ser.data})


class GarnishIngredientViewSet(PrettyNameMixin, viewsets.ModelViewSet):
    queryset = RecipeIngredient.objects.filter(garnish_for__isnull=False).order_by('name').distinct()

    serializer_class = GarnishIngredientSerializer
    lookup_field = 'name'
    renderer_classes = (CustomBrowsableAPIRenderer, JSONRenderer)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']

    def get_view_name(self):
        if getattr(self, 'action', None) == 'list' or not getattr(self, 'kwargs', {}).get('name'):
            return 'Garnish ingredients'
        try:
            obj = self.get_object()
            return getattr(obj, 'name', str(obj))
        except Exception:
            return super().get_view_name()

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(self.get_queryset(), many=True, context={"request": request})
        return Response({'results': serializer.data})

    def retrieve(self, request, pk=None, *args, **kwargs):
        name = kwargs.get('name') or pk
        if name is None:
            raise Http404
        if str(name).isdigit():
            ingredient = get_object_or_404(RecipeIngredient, pk=name)
        else:
            ingredient = _get_by_safe_name(RecipeIngredient, name)
        drinks_qs = Drink.objects.filter(garnish=ingredient).order_by('name').distinct()
        page = self.paginate_queryset(drinks_qs)
        if page is not None:
            drinks_ser = DrinkSerializer(page, many=True, context={"request": request, "suppress_category": True})
            return self.get_paginated_response(drinks_ser.data)
        drinks_ser = DrinkSerializer(drinks_qs, many=True, context={"request": request, "suppress_category": True})
        return Response({'results': drinks_ser.data})


class TagViewSet(PrettyNameMixin, viewsets.ModelViewSet):

    queryset = Tag.objects.all().annotate(drink_count=Count('drink', distinct=True)).order_by('name')
    serializer_class = TagSerializer
    renderer_classes = (CustomBrowsableAPIRenderer, JSONRenderer)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']
    def get_view_description(self, *args, **kwargs):
        req = kwargs.get('request') or getattr(self, 'request', None)
        if req is not None and getattr(req, 'accepted_renderer', None) is not None and req.accepted_renderer.format == 'html':
            return mark_safe(build_nav_html(req))
        if req:
            return mark_safe(build_nav_html(req))

    def retrieve(self, request, pk=None, *args, **kwargs):
        if pk is None:
            raise Http404
        if str(pk).isdigit():
            tag = get_object_or_404(Tag, pk=pk)
        else:
            tag = _get_by_safe_name(Tag, pk)
        drinks_qs = Drink.objects.filter(tags=tag).order_by('name').distinct()
        page = self.paginate_queryset(drinks_qs)
        if page is not None:
            drinks_ser = DrinkSerializer(page, many=True, context={"request": request, "suppress_category": True})
            return self.get_paginated_response(drinks_ser.data)
        drinks_ser = DrinkSerializer(drinks_qs, many=True, context={"request": request, "suppress_category": True})
        return Response({'results': drinks_ser.data})


class CategoryViewSet(PrettyNameMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'name'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']
    renderer_classes = (CustomBrowsableAPIRenderer, JSONRenderer)

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        """Return categories with preferred pseudo-categories first in the
    requested order: Cocktails throughout history, Shots, My Recipes,
    then the remaining categories alphabetically.
        """

        base = Category.objects.all()
        preferred = ['Cocktails throughout history', 'Shots', 'My Recipes']
        try:
            whens = []
            for idx, name in enumerate(preferred):
                whens.append(When(name__iexact=name, then=Value(idx)))
            order_case = Case(*whens, default=Value(100), output_field=IntegerField())
            return base.annotate(_pref_order=order_case).order_by('_pref_order', 'name')
        except Exception:
            return base.order_by('name')

    def get_view_name(self, *args, **kwargs):
        name = self.request.query_params.get("name") if hasattr(self, "request") else None
        try:
            if getattr(self, 'action', None) == 'retrieve' or getattr(self, 'kwargs', {}).get('name'):
                name = getattr(self, 'kwargs', {}).get('name')
                if name:
                    norm = str(name).replace('_', ' ').strip().lower()
                    if norm == 'cocktails throughout history':
                        return 'Cocktails Throughout History'
                    if norm == 'shots':
                        return 'Shots'
                    if norm in ('my recipes', 'my_recipes'):
                        return 'My Recipes'
                obj = self.get_object()
                return obj.name
        except Exception:
            pass
        try:
            req = getattr(self, 'request', None)
            if req is not None:
                try:
                    categories_full = reverse('category-list', request=req)
                    from urllib.parse import urlparse
                    categories_path = urlparse(categories_full).path
                except Exception:
                    categories_path = None

                if categories_path and req.path != categories_path:
                    return mark_safe('<span style="color:#777;">Categories</span>')
        except Exception:
            pass

        if name:
            return mark_safe(name)
        return mark_safe("Categories")

    def retrieve(self, request, slug=None, *args, **kwargs):
        name = kwargs.get('name') or slug
        if name is None:
            raise Http404
        category = None
        try:
            try:
                category = Category.objects.filter(name__iexact=str(name).replace('_', ' ')).first()
            except Exception:
                category = None
        except Exception:
            category = None

        if not category:
            try:
                category = _get_by_safe_name(Category, name)
            except Exception:
                category = None

        if not category:
            raise Http404

        if getattr(category, 'name', '').strip().lower() == 'cocktails throughout history':
            drinks = Drink.objects.filter(category__name__iexact='Cocktails Throughout History').order_by('name').distinct()
            if request.query_params.get('search'):
                drinks = drinks.filter(name__icontains=request.query_params.get('search'))
        elif getattr(category, 'name', '').strip().lower() == 'shots':
            drinks = Drink.objects.filter(is_shot=True).order_by('name')
            if request.query_params.get('search'):
                drinks = drinks.filter(name__icontains=request.query_params.get('search'))
        else:
            drinks = Drink.objects.filter(category=category).order_by('name')

        page = self.paginate_queryset(drinks)
        if page is not None:
            serializer = DrinkSerializer(page, many=True, context={"request": request, "suppress_category": True})
            return self.get_paginated_response(serializer.data)
        serializer = DrinkSerializer(drinks, many=True, context={"request": request, "suppress_category": True})
        return Response({'results': serializer.data})
    def get_view_description(self, *args, **kwargs):
        req = kwargs.get('request') or getattr(self, 'request', None)
        if req is not None and getattr(req, 'accepted_renderer', None) is not None and getattr(req.accepted_renderer, 'format', None) == 'html':
            nav = build_nav_html(req)
            if not req.query_params.get('name'):
                try:
                    categories = list(self.get_queryset())
                    links = []
                    for c in categories:
                        try:
                            from .serializers import safe_name_from as _safe_name_from
                            try:
                                href = reverse('category-detail', args=[_safe_name_from(c.name)], request=req)
                            except Exception:
                                href = f"{reverse('category-list', request=req)}?name={_safe_name_from(c.name)}"
                        except Exception:
                            href = f"{req.path.rstrip('/')}/{_safe_name_from(c.name)}/"
                        thumb_html = ''
                        try:
                            sample = Drink.objects.filter(category=c, image__isnull=False).first()
                            if sample and getattr(sample.image, 'url', None):
                                img_url = req.build_absolute_uri(sample.image.url)
                                thumb_html = f'<img src="{img_url}" style="width:48px;height:36px;object-fit:cover;border:1px solid #ddd;margin-right:8px;display:inline-block;vertical-align:middle;"/>'
                        except Exception:
                            thumb_html = ''
                        links.append(f'<li style="margin-bottom:8px;"><a href="{href}">{thumb_html}<span style="vertical-align:middle;">{c.name}</span></a></li>')
                    header_title = 'Categories'
                    try:
                        if req and '/categories/' in getattr(req, 'path', '') and req.path.rstrip('/').count('/') >= 3:
                            seg = req.path.rstrip('/').split('/')[-1]
                            try:
                                cat = Category.objects.filter(name__iexact=str(seg).replace('_', ' ')).first()
                                if not cat:
                                    cat = _get_by_safe_name(Category, seg)
                                if cat:
                                    header_title = cat.name
                            except Exception:
                                pass
                    except Exception:
                        pass

                    html = '<div class="category-links" style="margin-bottom:12px;">' + nav + f'<h2 style="margin-top:8px;">{header_title}</h2><ul style="list-style:disc;margin-left:20px;">' + ''.join(links) + '</ul></div>'
                    return mark_safe(html)
                except Exception:
                    return mark_safe(nav)
            return mark_safe(nav)

        if req:
            return mark_safe(build_nav_html(req))

        return super().get_view_description(*args, **kwargs)


class PreparationMethodViewSet(PrettyNameMixin, viewsets.ModelViewSet):
    queryset = PreparationMethod.objects.all().order_by('name')
    serializer_class = PreparationMethodSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']
    pagination_class = AdminAwarePagination
    renderer_classes = (CustomBrowsableAPIRenderer, JSONRenderer)

    def get_view_name(self):
        """Delegate to PrettyNameMixin so browsable UI shows the method name on detail pages."""
        try:
            return super().get_view_name()
        except Exception:
            return 'Preparation Methods'
    def get_view_description(self, *args, **kwargs):
        req = kwargs.get('request') or getattr(self, 'request', None)
        if req is not None and getattr(req, 'accepted_renderer', None) is not None and req.accepted_renderer.format == 'html':
            return mark_safe(build_nav_html(req))
        if req:
            return mark_safe(build_nav_html(req))
        return super().get_view_description(*args, **kwargs)

    def retrieve(self, request, pk=None, *args, **kwargs):
        if pk is None:
            raise Http404
        if str(pk).isdigit():
            prep = get_object_or_404(PreparationMethod, pk=pk)
        else:
            prep = _get_by_safe_name(PreparationMethod, pk)
        drinks_qs = Drink.objects.filter(preparation_method=prep).order_by('name').distinct()
        page = self.paginate_queryset(drinks_qs)
        if page is not None:
            drinks_ser = DrinkSerializer(page, many=True, context={"request": request, "suppress_category": True})
            return self.get_paginated_response(drinks_ser.data)
        drinks_ser = DrinkSerializer(drinks_qs, many=True, context={"request": request, "suppress_category": True})
        return Response({'results': drinks_ser.data})


class UnitViewSet(PrettyNameMixin, viewsets.ModelViewSet):
    queryset = Unit.objects.all().order_by('name')
    serializer_class = UnitSerializer
    renderer_classes = (CustomBrowsableAPIRenderer, JSONRenderer)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']

    def get_view_description(self, *args, **kwargs):
        req = kwargs.get('request') or getattr(self, 'request', None)
        if req is not None and getattr(req, 'accepted_renderer', None) is not None and req.accepted_renderer.format == 'html':
            return mark_safe(build_nav_html(req))
        if req:
            return mark_safe(build_nav_html(req))
        return super().get_view_description(*args, **kwargs)

    def get_view_name(self):
        """Return 'Units' for list view and the unit name for detail view."""
        try:
            return super().get_view_name()
        except Exception:
            return 'Units'
    def retrieve(self, request, pk=None, *args, **kwargs):
        if pk is None:
            raise Http404
        if str(pk).isdigit():
            unit = get_object_or_404(Unit, pk=pk)
        else:
            unit = _get_by_safe_name(Unit, pk)
        drinks_qs = Drink.objects.filter(recipe_ingredients__unit=unit).order_by('name').distinct()
        page = self.paginate_queryset(drinks_qs)
        if page is not None:
            drinks_ser = DrinkSerializer(page, many=True, context={"request": request, "suppress_category": True})
            return self.get_paginated_response(drinks_ser.data)
        drinks_ser = DrinkSerializer(drinks_qs, many=True, context={"request": request, "suppress_category": True})
        return Response({'results': drinks_ser.data})


class GlassTypeViewSet(PrettyNameMixin, viewsets.ModelViewSet):
    queryset = GlassType.objects.all().order_by('name')
    serializer_class = GlassTypeSerializer
    renderer_classes = (CustomBrowsableAPIRenderer, JSONRenderer)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']

    def get_view_description(self, *args, **kwargs):
        req = kwargs.get('request') or getattr(self, 'request', None)
        if req is not None and getattr(req, 'accepted_renderer', None) is not None and req.accepted_renderer.format == 'html':
            return mark_safe(build_nav_html(req))
        if req:
            return mark_safe(build_nav_html(req))
        return super().get_view_description(*args, **kwargs)
    def retrieve(self, request, pk=None, *args, **kwargs):
        if pk is None:
            raise Http404
        if str(pk).isdigit():
            glass = get_object_or_404(GlassType, pk=pk)
        else:
            glass = _get_by_safe_name(GlassType, pk)
        drinks_qs = Drink.objects.filter(glass_type=glass).order_by('name').distinct()
        page = self.paginate_queryset(drinks_qs)
        if page is not None:
            drinks_ser = DrinkSerializer(page, many=True, context={"request": request, "suppress_category": True})
            return self.get_paginated_response(drinks_ser.data)
        drinks_ser = DrinkSerializer(drinks_qs, many=True, context={"request": request, "suppress_category": True})
        return Response({'results': drinks_ser.data})


class ReimportView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        return Response({'detail': 'Import endpoints have been removed from this installation.'}, status=status.HTTP_404_NOT_FOUND)

    def retrieve(self, request, pk=None, *args, **kwargs):
        raise Http404


from django.shortcuts import render
from django.views import View

class GalleryView(View):
    def get(self, request):

        drinks_with_images = Drink.objects.filter(
            image__isnull=False
        ).exclude(
            image=''
        ).order_by('name')

        context = {
            'drinks': drinks_with_images,
            'total_images': drinks_with_images.count()
        }
        return render(request, 'gallery.html', context)


class ContactView(APIView):
    def post(self, request):
        name = request.data.get('name')
        email = request.data.get('email')
        message = request.data.get('message')

        if not name or not email or not message:
            return Response({'error': 'Please provide all fields'}, status=status.HTTP_400_BAD_REQUEST)


        subject = f"New Message from {name} (Aristotelis Bar Book)"
        full_message = f"Sender: {name} <{email}>\n\nMessage:\n{message}"

        try:
            send_mail(
                subject,
                full_message,
                'noreply@aristotelis.bar',
                ['telis.aslanidis.io@gmail.com'],
                fail_silently=False,
            )
            return Response({'success': 'Message sent successfully!'}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Email Error: {e}")
            return Response({'error': 'Failed to send message'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
