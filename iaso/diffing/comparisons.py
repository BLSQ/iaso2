from django.contrib.gis.geos import Point


class Dictable:
    def as_dict(self):
        return self.__dict__

    def __str__(self):
        return "{} {}".format(self.__class__.__name__, self.as_dict())


class FieldType(Dictable):
    def __init__(self, field_name):
        self.field_name = field_name

    def is_same(self, value, other_value):
        return value == other_value

    def distance(self, dhis2_value, ref_value):
        return None


class NameFieldType(FieldType):
    def access(self, org_unit):
        if org_unit is None:
            return None
        return org_unit.name


class GeometryFieldType(FieldType):
    def access(self, org_unit):
        if org_unit is None:
            return None
        if org_unit.location:
            return org_unit.location
        if org_unit.geom:
            return org_unit.geom
        if org_unit.simplified_geom:
            return org_unit.simplified_geom
        return None

    def distance(self, dhis2_value, ref_value):
        if isinstance(dhis2_value, Point) and isinstance(ref_value, Point):
            # TODO  is this the good way to calculate the distances ?
            # https://docs.djangoproject.com/en/2.2/ref/contrib/gis/geos/#django.contrib.gis.geos.GEOSGeometry.distance
            return dhis2_value.distance(ref_value) * 100  # approx km ?
        return None


class ParentFieldType(FieldType):
    def access(self, org_unit):
        if org_unit is None:
            return None

        if org_unit.parent:
            return org_unit.parent.source_ref
        return None


class GroupSetFieldType(FieldType):
    def __init__(self, field_name):
        super().__init__(field_name)
        self.groupset_ref = field_name.split(":")[1]
        self.groupset_name = field_name.split(":")[2]

    def access(self, org_unit):
        if org_unit is None:
            return None
        groups = []
        for group in org_unit.groups.all():
            for groupset in group.group_sets.all():
                if groupset.source_ref == self.groupset_ref:
                    groups.append({"id": group.source_ref, "name": group.name})

        return groups

    def is_same(self, value, other_value):
        val = sorted(map(lambda g: g["id"], value or []))
        other_val = sorted(map(lambda g: g["id"], other_value or []))
        return val == other_val


class GroupFieldType(FieldType):
    def __init__(self, field_name):
        super().__init__(field_name)
        self.group_ref = field_name.split(":")[1]
        self.group_name = field_name.split(":")[2]

    def access(self, org_unit):
        if org_unit is None:
            return None
        groups = []
        for group in org_unit.groups.all():
            if group.source_ref == self.group_ref:
                groups.append({"id": group.source_ref, "name": group.name})

        return groups

    def is_same(self, value, other_value):
        val = sorted(map(lambda g: g["id"], value or []))
        other_val = sorted(map(lambda g: g["id"], other_value or []))
        return val == other_val


class OpeningDateFieldType(FieldType):
    def access(self, org_unit):
        if org_unit is None:
            return None
        return org_unit.opening_date


class ClosedDateFieldType(FieldType):
    def access(self, org_unit):
        if org_unit is None:
            return None
        return org_unit.closed_date


def as_field_types(field_names):
    field_types = []
    for field_name in field_names:
        if field_name == "name":
            field_types.append(NameFieldType(field_name))
        elif field_name == "geometry":
            field_types.append(GeometryFieldType(field_name))
        elif field_name == "parent":
            field_types.append(ParentFieldType(field_name))
        elif field_name.startswith("groupset:"):
            field_types.append(GroupSetFieldType(field_name))
        elif field_name.startswith("group:"):
            field_types.append(GroupFieldType(field_name))
        elif field_name == "opening_date":
            field_types.append(OpeningDateFieldType(field_name))
        elif field_name == "closed_date":
            field_types.append(ClosedDateFieldType(field_name))
        else:
            raise Exception("Unsupported field : '" + field_name + "'")
    return field_types


class Diff(Dictable):
    def __init__(self, orgunit_ref, orgunit_dhis2, status, comparisons):
        self.org_unit = orgunit_ref if orgunit_ref else orgunit_dhis2
        self.orgunit_ref = orgunit_ref
        self.orgunit_dhis2 = orgunit_dhis2
        self.status = status
        self.comparisons = comparisons

    def comparison(self, field):
        try:
            return next(x for x in self.comparisons if x.field == field)
        except StopIteration:
            return None

    def are_fields_modified(self, fields):
        return len(list(x for x in self.comparisons if x.field in fields and x.status != "same")) > 0


class Comparison(Dictable):
    def __init__(self, field, status, before, after, distance):
        self.field = field
        self.before = before
        self.after = after
        self.status = status
        self.distance = distance
