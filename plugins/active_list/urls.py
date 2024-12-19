from django.urls import path, re_path
from . import views

urlpatterns = [
    path("homepage/", views.homepage, name="homepage"),
    path("patient_list/", views.patient_list, name="patient_list"),
    path("patient_list_api/<int:org_unit_id>/<str:period>/", views.patient_list_api, name="patient_list_api"),
    path("upload/", views.upload, name="upload"),
    path("validation_api/<int:org_unit_id>/<str:period>/", views.validation_api, name="validation_api"),
    re_path(
        r"^validation/$",
        views.validation,
        name="validation",
    ),
]
