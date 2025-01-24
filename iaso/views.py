import json

import clamav_client
from bs4 import BeautifulSoup as Soup  # type: ignore
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.views import redirect_to_login
from django.db import models
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, resolve_url
from django.views.generic import TemplateView
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.openapi import ReferenceResolver

from hat.__version__ import DEPLOYED_BY, DEPLOYED_ON, VERSION
from iaso.models import IFRAME, POWERBI, SUPERSET, TEXT, Account, Page
from iaso.utils.powerbi import get_powerbi_report_token


def load_powerbi_config_for_page(page: Page):
    group_id = page.powerbi_group_id
    report_id = page.powerbi_report_id
    filters = page.powerbi_filters
    language = page.powerbi_language

    report_access_token = get_powerbi_report_token(group_id, report_id)
    config = {
        "token": report_access_token,
        "report_id": report_id,
        "group_id": group_id,
        "language": language,
        "filters": filters,
    }
    return config


def page(request, page_slug):
    content = {}

    try:
        analytics_script = request.user.iaso_profile.account.analytics_script
    except AttributeError:
        analytics_script = None

    if analytics_script:
        content["analytics_script"] = analytics_script
    page = get_object_or_404(Page, slug=page_slug)
    path = request.get_full_path()
    resolved_login_url = resolve_url(settings.LOGIN_URL)
    if page.needs_authentication and ((not request.user.is_authenticated) or (request.user not in page.users.all())):
        return redirect_to_login(path, resolved_login_url, "next")
    if page.type == IFRAME:
        content.update({"src": page.content, "title": page.name, "page": page})
        response = render(
            request,
            "iaso/pages/iframe.html",
            content,
        )
    elif page.type == TEXT:
        content.update(
            {
                "text": page.content,
                "title": page.name,
            }
        )
        response = render(
            request,
            "iaso/pages/text.html",
            content,
        )
    elif page.type == POWERBI:
        config = load_powerbi_config_for_page(page)
        content.update(
            {
                "config": config,
                "title": page.name,
                "page": page,
            }
        )

        response = render(
            request,
            "iaso/pages/powerbi.html",
            content,
        )
    elif page.type == SUPERSET:
        content.update(
            {
                "config": {
                    "superset_url": settings.SUPERSET_URL,
                    "dashboard_id": page.superset_dashboard_id,
                    "dashboard_ui_config": page.superset_dashboard_ui_config,
                },
                "title": page.name,
                "page": page,
            }
        )
        response = render(
            request,
            "iaso/pages/superset.html",
            content,
        )
    else:
        raw_html = page.content
        if analytics_script and raw_html is not None:
            raw_html = addTag(raw_html, analytics_script)
        response = HttpResponse(raw_html)
    response["X-Frame-Options"] = "ALLOW"
    return response


# Function to append analytics script in the head tag
def addTag(html, tagToAppend):
    soup = Soup(html, "html.parser")
    if not soup.head:
        head = soup.new_tag("head")
        if soup.html:
            soup.html.insert(1, head)
        else:
            soup.insert(1, head)
    soup.head.append(Soup(tagToAppend, "html.parser"))
    return soup


def health(request):
    """This is used by aws health check to verify the environment is up

    it just looks at the 200 status code and not at the content.
    """
    res = {
        "up": "ok",
        "env": settings.ENVIRONMENT,
        "database": settings.DATABASES["default"]["NAME"],
        "DEPLOYED_ON": DEPLOYED_ON,
        "DEPLOYED_BY": DEPLOYED_BY,
        "VERSION": VERSION,
    }
    # noinspection PyBroadException
    try:
        # mostly to check we can connect to the db
        res["account_count"] = Account.objects.count()
    except:
        res["error"] = "db_fail"

    return JsonResponse(res)


def health_clamav(request):
    """This is used to check whether ClamAV is active on this Iaso instance and if the ClamAV server is reachable
    """

    is_clamav_active = settings.CLAMAV_ACTIVE
    if not is_clamav_active:
        return JsonResponse({"active": False, "up": "?"})

    ping_config = {
        **settings.CLAMAV_CONFIGURATION,
        "timeout": float(2),
    }

    scanner = clamav_client.get_scanner(config=ping_config)
    res = {
        "active": True,
    }

    try:
        info = scanner.info()
        res["up"] = True
        res["version"] = info.version
        res["virus_definitions"] = info.virus_definitions
    except Exception:
        res["up"] = False

    return JsonResponse(res)


def robots_txt(request):
    content = """User-agent: *
Disallow: /"""
    return HttpResponse(content, content_type="text/plain")


import json

from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from django.shortcuts import render
from django.views import View

from iaso import models as iaso_models


class ModelDataView(View):
    def get(self, request, *args, **kwargs):
        model_data = self.get_model_data()
        return render(request, "iaso/model_diagram.html", {"model_data": json.dumps(model_data)})

    def get_model_data(self):
        nodes = []
        links = []

        all_models = [
            getattr(iaso_models, name)
            for name in dir(iaso_models)
            if isinstance(getattr(iaso_models, name), type) and issubclass(getattr(iaso_models, name), models.Model)
        ]

        for model in all_models:
            node = {"id": model.__name__, "type": "model", "app": "iaso", "fields": []}

            for field in model._meta.get_fields():
                field_type = self.get_field_type(field)
                node["fields"].append({"name": field.name, "type": field_type})

                if isinstance(field, (models.ForeignKey, models.OneToOneField, models.ManyToManyField)):
                    related_model = field.related_model
                    if related_model in all_models:
                        links.append(
                            {"source": model.__name__, "target": related_model.__name__, "type": type(field).__name__}
                        )

            nodes.append(node)

        return {"nodes": nodes, "links": links}

    def get_field_type(self, field):
        if isinstance(field, models.ForeignKey):
            return f"ForeignKey to {field.related_model.__name__}"
        elif isinstance(field, models.ManyToManyField):
            return f"ManyToManyField to {field.related_model.__name__}"
        elif isinstance(field, models.OneToOneField):
            return f"OneToOneField to {field.related_model.__name__}"
        elif isinstance(field, GenericForeignKey):
            return "GenericForeignKey"
        else:
            return field.__class__.__name__
