import json
from typing import Any, Dict

from django.conf import settings
from django.http.request import HttpRequest


def appversions(request: HttpRequest) -> Dict[str, bool]:
    return {"DEV_SERVER": settings.DEV_SERVER}


def app_title(request: HttpRequest) -> Dict[str, str]:
    return {"app_title": settings.APP_TITLE}


def favicon_path(request: HttpRequest) -> Dict[str, str]:
    return {"favicon_path": settings.FAVICON_PATH}


def logo_path(request: HttpRequest) -> Dict[str, str]:
    return {"logo_path": settings.LOGO_PATH}


def sentry_config(request: HttpRequest) -> Dict[str, Any]:
    config = {
        "sentry_config": {
            "SENTRY_URL": settings.SENTRY_URL or None,
            "SENTRY_ENVIRONMENT": settings.ENVIRONMENT or None,
            "SENTRY_FRONT_ENABLED": settings.SENTRY_FRONT_ENABLED or None,
        }
    }
    return {"sentry_config": json.dumps(config["sentry_config"])}


def learn_more_url(request: HttpRequest) -> Dict[str, Any]:
    return {"LEARN_MORE_URL": settings.LEARN_MORE_URL}


def theme(request: HttpRequest) -> Dict[str, Any]:
    return {
        # TODO: Duplicated data: refactor?
        "THEME_PRIMARY_COLOR": settings.THEME_PRIMARY_COLOR,
        "THEME_SECONDARY_COLOR": settings.THEME_SECONDARY_COLOR,
        "THEME_PRIMARY_BACKGROUND_COLOR": settings.THEME_PRIMARY_BACKGROUND_COLOR,
        "theme": {
            "THEME_PRIMARY_COLOR": settings.THEME_PRIMARY_COLOR,
            "THEME_SECONDARY_COLOR": settings.THEME_SECONDARY_COLOR,
            "THEME_PRIMARY_BACKGROUND_COLOR": settings.THEME_PRIMARY_BACKGROUND_COLOR,
            "LOGO_PATH": settings.LOGO_PATH,
            "FAVICON_PATH": settings.FAVICON_PATH,
            "APP_TITLE": settings.APP_TITLE,
            "SHOW_NAME_WITH_LOGO": settings.SHOW_NAME_WITH_LOGO,
        },
    }
