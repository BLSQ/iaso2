import importlib
from importlib import import_module

import django_sql_dashboard  # type: ignore
from django.apps import apps
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin, auth
from django.db import models
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import include, path, re_path
from django.views.generic import RedirectView, TemplateView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from iaso.views import ModelDataView, health, page, robots_txt, health_clamav

admin.site.site_header = "Administration de Iaso"
admin.site.site_title = "Iaso"
admin.site.index_title = "Administration de Iaso"


if settings.MAINTENANCE_MODE:
    urlpatterns = [
        path("_health/", health),
        path("_health", health),  # same without slash otherwise AWS complain about redirect
        path("health/", health),  # alias since current apache config hide _health/
        path("health-clamav/", health_clamav),
    ]

    def custom_404_view(request, exception):
        return render(request, "iaso/maintenance.html", {}, status=404)

    handler404 = custom_404_view
else:
    if settings.DISABLE_PASSWORD_LOGINS:
        login_template = "iaso/disabled_password_login.html"
        urlpatterns = [
            path("admin/login/", TemplateView.as_view(template_name=login_template), name="admin-login"),
            path("login/", TemplateView.as_view(template_name=login_template), name="login"),
        ]
    else:
        login_template = "iaso/login.html"
        urlpatterns = [
            path("admin/login/", auth.views.LoginView.as_view(template_name=login_template), name="admin-login"),
            path("login/", auth.views.LoginView.as_view(template_name=login_template), name="login"),
        ]

    if settings.ACTIVATE_SOCIAL_ACCOUNT:
        # ------------------ adding urls of allauth for social account ------------------
        # this snippet is lifted from allauth.account.urls.py. It's the only way I found to ONLY load the features we need
        # It means that with the current allauth version, only the following urls will be added (for a WFP account):
        # /accounts/wfp/login/	allauth.socialaccount.providers.oauth2.views.view	wfp_login
        # /accounts/wfp/login/callback/	allauth.socialaccount.providers.oauth2.views.view	wfp_callback
        # /accounts/wfp/token/	plugins.wfp_auth.views.token_view	wfp_token
        from allauth.socialaccount import providers

        # Provider urlpatterns, as separate attribute (for reusability).
        provider_urlpatterns = []
        for provider in providers.registry.get_list():
            try:
                prov_mod = import_module(provider.get_package() + ".urls")
            except ImportError:
                continue
            prov_urlpatterns = getattr(prov_mod, "urlpatterns", None)
            if prov_urlpatterns:
                provider_urlpatterns += prov_urlpatterns
        urlpatterns += [path("accounts/", include(provider_urlpatterns))]

    urlpatterns += [
        path("robots.txt", robots_txt),
        path("", RedirectView.as_view(pattern_name="dashboard:home_iaso", permanent=False), name="index"),
        path("_health/", health),
        path("_health", health),  # same without slash otherwise AWS complain about redirect
        path("health/", health),  # alias since current apache config hide _health/
        path("health-clamav/", health_clamav),
        path("admin/", admin.site.urls),
        path("api/", include("iaso.urls")),
        path("pages/<page_slug>/", page, name="pages"),
        path("i18n/", include("django.conf.urls.i18n")),
        path("logout-iaso", auth.views.LogoutView.as_view(next_page="/login/"), name="logout-iaso"),
        path(
            "forgot-password/",
            auth.views.PasswordResetView.as_view(
                template_name="iaso/forgot_password.html",
                email_template_name="iaso/reset_password_email.html",
                subject_template_name="iaso/reset_password_subject.txt",
                success_url="/forgot-password-confirmation/",
            ),
            name="forgot_password",
        ),
        path(
            "forgot-password-confirmation/",
            auth.views.PasswordResetDoneView.as_view(template_name="iaso/forgot_password_confirmation.html"),
            name="forgot_password_confirmation",
        ),
        path(
            "reset-password-confirmation/<uidb64>/<token>/",
            auth.views.PasswordResetConfirmView.as_view(
                template_name="iaso/reset_password_confirmation.html", success_url="/reset-password-complete/"
            ),
            name="reset_password_confirmation",
        ),
        path(
            "reset-password-complete/",
            auth.views.PasswordResetCompleteView.as_view(template_name="iaso/reset_password_complete.html"),
            name="reset_password_complete",
        ),
        path("sync/", include("hat.sync.urls")),
        path("models/", ModelDataView.as_view(), name="models"),
    ]

    for plugin_name in settings.PLUGINS:
        urls_module_name = "plugins." + plugin_name + ".urls"
        urls_module = importlib.util.find_spec(urls_module_name)  # checking if the urls module exists for this plugin

        if urls_module:
            urlpatterns = urlpatterns + [
                path(plugin_name + "/", include(urls_module_name)),
            ]
        else:
            print(f"URL module not found for plugin: {plugin_name}")

    # Swagger config
    schema_view = get_schema_view(
        openapi.Info(
            title="Iaso",
            default_version="v1",
            description="Iaso Swagger",
        ),
        public=False,
        urlconf="hat.urls",
        permission_classes=(permissions.IsAdminUser,),
    )

    urlpatterns = urlpatterns + [
        re_path(r"^swagger(?P<format>\.json|\.yaml)$", schema_view.without_ui(cache_timeout=0), name="schema-json"),
        path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
        path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    ]

    if settings.BEANSTALK_WORKER or settings.DEBUG or settings.IN_TESTS:
        urlpatterns.append(path("tasks/", include("beanstalk_worker.urls")))

    if apps.is_installed("django_sql_dashboard"):
        from django_sql_dashboard_export.views import export_sql_results_for_dashboard

        urlpatterns.append(path("explore/", include(django_sql_dashboard.urls)))
        urlpatterns.append(path("explore/<slug>/export/", export_sql_results_for_dashboard))

    urlpatterns.append(path("dashboard/", include("hat.dashboard.urls")))

    urlpatterns += static(settings.MEDIA_URL_PREFIX, document_root=settings.MEDIA_ROOT)

    if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:
        urlpatterns = [path("__debug__/", include("debug_toolbar.urls"))] + urlpatterns
