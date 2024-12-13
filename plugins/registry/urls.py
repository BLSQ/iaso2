from django.urls import re_path

from hat.dashboard import views

app_name = "registry"
urlpatterns = [
    re_path(r"^.*$", views.public_iaso, name="registry"),
]
