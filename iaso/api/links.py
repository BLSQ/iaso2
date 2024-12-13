from copy import deepcopy
from time import gmtime, strftime

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import StreamingHttpResponse, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, serializers
from rest_framework.response import Response

from hat.api.export_utils import Echo, generate_xlsx, iter_items
from hat.audit.models import log_modification, ORG_UNIT_API
from iaso.api.common import CONTENT_TYPE_XLSX, CONTENT_TYPE_CSV
from iaso.models import Link, OrgUnit, DataSource
from iaso.utils import geojson_queryset
from hat.menupermissions import models as permission


class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Link
        fields = ["id", "destination", "source", "validated", "similarity_score", "algorithm_run"]

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        account = self.context["request"].user.iaso_profile.account
        sources = DataSource.objects.filter(projects__account=account)
        run = attrs["algorithm_run"]

        if not (run.version_1.data_source in sources and run.version_2.data_source in sources):
            raise serializers.ValidationError("This run is not part of your account.")
        link_source = attrs["source"]
        link_destination = attrs["destination"]
        # print(link_source.version, run.version_1)
        # print(link_destination.version, run.version_2)
        if not (link_source.version == run.version_2 and link_destination.version == run.version_1):
            raise serializers.ValidationError("Your source and destination are not matching with the run")

        return validated_data


class LinkViewSet(viewsets.ViewSet):
    f"""Links API

    This API is restricted to authenticated users having the "{permission.LINKS}" permission

    GET /api/links/
    POST /api/links/
    GET /api/links/<id>
    PATCH /api/links/<id>
    """

    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        limit = request.GET.get("limit", None)
        page_offset = request.GET.get("page", 1)
        order = request.GET.get("order", "id").split(",")
        validated = request.GET.get("validated", None)
        search = request.GET.get("search", None)

        org_unit_type_id = request.GET.get("orgUnitTypeId", None)
        org_unit_id = request.GET.get("orgUnitId", None)
        origin = request.GET.get("origin", None)
        destination = request.GET.get("destination", None)
        origin_version = request.GET.get("originVersion", None)
        destination_version = request.GET.get("destinationVersion", None)
        validator_id = request.GET.get("validatorId", None)
        algorithm_id = request.GET.get("algorithmId", None)
        algorithm_run_id = request.GET.get("algorithmRunId", None)
        run_id = request.GET.get("run", None)
        score = request.GET.get("score", None)
        csv_format = request.GET.get("csv", None)
        xlsx_format = request.GET.get("xlsx", None)
        queryset = Link.objects.order_by(*order)

        if not request.user.is_anonymous:
            profile = request.user.iaso_profile
            queryset = queryset.filter(source__version__data_source__projects__account=profile.account)

        if search:
            queryset = queryset.filter(
                Q(destination__name__icontains=search) | Q(destination__aliases__contains=[search])
            )
            queryset = queryset.filter(Q(source__name__icontains=search) | Q(source__aliases__contains=[search]))

        if validated == "true":
            queryset = queryset.filter(validated=True)
        if validated == "false":
            queryset = queryset.filter(validated=False)
        if org_unit_id:
            queryset = queryset.filter(Q(destination__id=org_unit_id) | Q(source__id=org_unit_id))
        if destination:
            queryset = queryset.filter(destination__version__data_source_id=destination)

        if origin:
            queryset = queryset.filter(source__version__data_source_id=origin)

        if destination_version:
            queryset = queryset.filter(destination__version__number=destination_version)

        if origin_version:
            queryset = queryset.filter(source__version__number=origin_version)

        if validator_id:
            validator_id = int(validator_id)
            queryset = queryset.filter(validator=validator_id)

        if algorithm_id:
            queryset = queryset.filter(algorithm_run__algorithm=algorithm_id)

        if algorithm_run_id:
            queryset = queryset.filter(algorithm_run_id=algorithm_run_id)

        if run_id:
            queryset = queryset.filter(algorithm_run=run_id)
        if score:
            score_list = score.split(",")
            score_lower_bound = score_list[0]
            score_upper_bound = score_list[1]
            if score_lower_bound:
                queryset = queryset.filter(similarity_score__gte=score_lower_bound)

            if score_upper_bound:
                queryset = queryset.filter(similarity_score__lte=score_upper_bound)

        if org_unit_type_id:
            queryset = queryset.filter(
                Q(destination__org_unit_type_id__in=org_unit_type_id.split(","))
                | Q(source__org_unit_type_id__in=org_unit_type_id.split(","))
            )
        queryset = queryset.distinct()
        if csv_format is None and xlsx_format is None:
            if limit:
                limit = int(limit)
                page_offset = int(page_offset)

                paginator = Paginator(queryset, limit)
                res = {"count": paginator.count}
                if page_offset > paginator.num_pages:
                    page_offset = paginator.num_pages
                page = paginator.page(page_offset)

                res["links"] = map(lambda x: x.as_dict(), page.object_list)
                res["has_next"] = page.has_next()
                res["has_previous"] = page.has_previous()
                res["page"] = page_offset
                res["pages"] = paginator.num_pages
                res["limit"] = limit
                return Response(res)
            else:
                queryset = queryset
                return Response({"links": [link.as_dict() for link in queryset]})
        else:
            columns = [
                {"title": "ID", "width": 20},
                {"title": "Run", "width": 20},
                {"title": "Destination", "width": 20},
                {"title": "Source", "width": 20},
                {"title": "Validated", "width": 40},
                {"title": "Validator", "width": 20},
                {"title": "Validation Date", "width": 20},
                {"title": "Creation Date", "width": 20},
                {"title": "Score", "width": 20},
            ]

            filename = "links"
            filename = "{}-{}".format(filename, strftime("%Y-%m-%d-%H-%M", gmtime()))

            def get_row(link, **kwargs):
                return [
                    link.id,
                    link.algorithm_run_id,
                    link.destination_id,
                    link.source_id,
                    link.validated,
                    link.validator_id,
                    link.validation_date,
                    link.created_at,
                    link.similarity_score,
                ]

            if xlsx_format:
                filename = filename + ".xlsx"
                response = HttpResponse(
                    generate_xlsx("Forms", columns, queryset, get_row),
                    content_type=CONTENT_TYPE_XLSX,
                )
            if csv_format:
                response = StreamingHttpResponse(
                    streaming_content=(iter_items(queryset, Echo(), columns, get_row)), content_type=CONTENT_TYPE_CSV
                )
                filename = filename + ".csv"
            response["Content-Disposition"] = "attachment; filename=%s" % filename
            return response

    def partial_update(self, request, pk=None):
        link = get_object_or_404(Link, id=pk)
        original_copy = deepcopy(link)
        validated = request.data.get("validated", None)
        if validated is not None:
            link.validated = validated
        if validated == True:
            link.validator = request.user
        if validated == False:
            link.validator = None

        log_modification(original_copy, link, source=ORG_UNIT_API, user=request.user)
        link.save()

        res = link.as_dict()

        return Response(res)

    def retrieve(self, request, pk=None):
        link = get_object_or_404(Link, id=pk)
        res = link.as_full_dict()
        res["source"]["geo_json"] = None
        res["destination"]["geo_json"] = None
        if link.source.simplified_geom:
            queryset = OrgUnit.objects.all().filter(id=link.source.id)
            res["source"]["geo_json"] = geojson_queryset(queryset, geometry_field="simplified_geom")
        if link.destination.simplified_geom:
            queryset = OrgUnit.objects.all().filter(id=link.destination.id)
            res["destination"]["geo_json"] = geojson_queryset(queryset, geometry_field="simplified_geom")
        return Response(res)

    def create(self, request):
        link_serializer = LinkSerializer(data=request.data, context={"request": request})
        link_serializer.is_valid(raise_exception=True)
        link = link_serializer.save()
        link.validator = request.user
        return Response(link.as_dict())
