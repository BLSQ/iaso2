from django.urls import path
from .views import debug, delete_beneficiaries_analytics, delete_all_instances_and_entities


urlpatterns = [
    path("debug/<int:id>/", debug, name="wfp_debug"),
    path("delete_beneficiaries_analytics/", delete_beneficiaries_analytics, name="delete_beneficiaries_analytics"),
    path(
        "delete_all_instances_and_entities/",
        delete_all_instances_and_entities,
        name="delete_all_instances_and_entities",
    ),
]
