from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework import viewsets, permissions
from django.contrib.auth.models import Permission
from django.db.models import Q, QuerySet
from rest_framework.response import Response
from iaso.models import UserRole
from django.core.paginator import Paginator


class HasRolesPermission(permissions.BasePermission):
    def has_permission(self, request: Request, view) -> bool:
        if not request.user.has_perm("menupermissions.iaso_user_roles"):
            return False
        return True


class UserRolesViewSet(viewsets.ViewSet):
    """Roles API

    This API is restricted to authenticated users having the "menupermissions.iaso_user_roles" permission for write permission
    Read access is accessible to any authenticated users as it necessary to list roles or display a particular one in
    the interface.

    GET /api/roles/
    GET /api/roles/<id>
    PATCH /api/roles/<id>
    DELETE /api/roles/<id>
    """

    # FIXME : replace by a model viewset

    permission_classes = [permissions.IsAuthenticated, HasRolesPermission]

    def get_queryset(self) -> QuerySet[UserRole]:
        return UserRole.objects.all()

    def list(self, request: Request) -> Response:
        limit_str = request.GET.get("limit", None)
        page_offset = request.GET.get("page", 1)
        orders = request.GET.get("order", "group__name").split(",")
        search = request.GET.get("search", None)
        queryset = self.get_queryset()

        if search:
            queryset = queryset.filter(Q(group__name__icontains=search)).distinct()

        if limit_str:
            queryset = queryset.order_by(*orders)
            limit = int(limit_str)
            page_offset = int(page_offset)
            paginator = Paginator(queryset, limit)
            res = {"count": paginator.count}
            if page_offset > paginator.num_pages:
                page_offset = paginator.num_pages
            page = paginator.page(page_offset)

            res["user_roles"] = map(lambda x: x.as_dict(), page.object_list)
            res["has_next"] = page.has_next()
            res["has_previous"] = page.has_previous()
            res["page"] = page_offset
            res["pages"] = paginator.num_pages
            res["limit"] = limit
            return Response(res)
        else:
            return Response({"user_roles": [userrole.as_short_dict() for userrole in queryset]})

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        pk = kwargs.get("pk")
        userRole = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(userRole.as_dict())

    def partial_update(self, request: Request, pk: int = None) -> Response:
        userRole = get_object_or_404(self.get_queryset(), id=pk)
        group = userRole.group
        permissions = request.data.get("permissions", [])
        group.permissions.clear()
        for permission_codename in permissions:
            permission = get_object_or_404(Permission, codename=permission_codename)
            group.permissions.add(permission)
        group.save()
        userRole.save()
        return Response(userRole.as_dict())

    def delete(self, request: Request, pk: int = None) -> Response:
        userRole = get_object_or_404(self.get_queryset(), id=pk)
        userRole.delete()
        return Response(True)
