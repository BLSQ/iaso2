from django.urls import path

from .provider import WFPProvider
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from . import views

urlpatterns = default_urlpatterns(WFPProvider)
urlpatterns += [
    path("wfp/login/callback", views.oauth2_callback, name="wfp_callback2"),
    path("wfp/token/", views.token_view, name="wfp_token"),
]
