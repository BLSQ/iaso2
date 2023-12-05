from django.contrib.gis.geos import Point
from django.db import IntegrityError, InternalError, connections
from django.db.models import Q

from iaso import models as m
from iaso.test import TestCase
from iaso.models.data_store import JsonDataStore


class OrgUnitTypeModelTestCase(TestCase):
    """OrgUnitType: tests at the business logic/model level"""

    @classmethod
    def setUpTestData(cls):
        cls.account = m.Account.objects.create(name="a")
        cls.project = m.Project.objects.create(name="Project 1", account=cls.account, app_id="test_app_id")
        cls.setup_out = m.OrgUnitType.objects.create(name="AS", depth=4)
        cls.setup_out.projects.add(cls.project)


class OrgUnitManagerTestCase(TestCase):
    def test_parents_q(self):
        country = m.OrgUnit.objects.create(
            name="ANGOLA",
            org_unit_type=m.OrgUnitType.objects.create(category="COUNTRY"),
            validation_status=m.OrgUnit.VALIDATION_VALID,
            path=["foo"],
        )
        region = m.OrgUnit.objects.create(
            name="HUILA",
            parent=country,
            org_unit_type=m.OrgUnitType.objects.create(category="REGION"),
            validation_status=m.OrgUnit.VALIDATION_VALID,
            path=["foo", "bar"],
        )
        district = m.OrgUnit.objects.create(
            name="CUVANGO",
            parent=region,
            org_unit_type=m.OrgUnitType.objects.create(category="DISTRICT"),
            validation_status=m.OrgUnit.VALIDATION_VALID,
            path=["foo", "bar", "baz"],
        )
        district.calculate_paths()
        q = m.OrgUnit.objects.parents_q(m.OrgUnit.objects.all())

        self.assertIsInstance(q, Q)
        path, args, kwargs = q.deconstruct()
        self.assertEqual(path, "django.db.models.Q")
        self.assertIn(("path__ancestors", country.path), args)
        self.assertIn(("path__ancestors", region.path), args)
        self.assertIn(("path__ancestors", district.path), args)
        self.assertEqual(kwargs, {"_connector": "OR"})


class OrgUnitModelTestCase(TestCase):
    """OrgUnit: tests at the business logic/model level"""

    @classmethod
    def setUpTestData(cls):
        cls.sector = m.OrgUnitType.objects.create(name="Sector", short_name="Sec")
        cls.system = m.OrgUnitType.objects.create(name="System", short_name="Sys")
        cls.jedi_council = m.OrgUnitType.objects.create(name="Jedi Council", short_name="Cnc")
        cls.jedi_task_force = m.OrgUnitType.objects.create(name="Jedi Task Force", short_name="Jtf")

    def test_org_unit_creation_no_parent_or_parent_has_path(self):
        """Newly created org unit without parents should have a path, and so do new org units
        attached to a parent that has a path."""

        corrusca = m.OrgUnit.objects.create(org_unit_type=self.sector, name="Corrusca Sector")
        corruscant = m.OrgUnit.objects.create(parent=corrusca, org_unit_type=self.sector, name="Corruscant System")
        self.assertEqual(str(corrusca.path), str(corrusca.pk))
        self.assertEqual(str(corruscant.path), f"{corrusca.pk}.{corruscant.pk}")

    def test_org_unit_creation_or_update_parent_without_path(self):
        """Created or updated a org unit linked to a pathless parent should not have a path."""

        corrusca = m.OrgUnit(org_unit_type=self.sector, name="Corrusca Sector")
        corrusca.save(skip_calculate_path=True)
        corruscant = m.OrgUnit.objects.create(parent=corrusca, org_unit_type=self.sector, name="Corruscant System")
        self.assertIsNone(corruscant.path)
        corruscant.save()
        self.assertIsNone(corruscant.path)

    def test_org_unit_update_path_with_children(self):
        """Path should be set for the whole hierarchy"""

        corrusca = m.OrgUnit(org_unit_type=self.sector, name="Corrusca Sector")
        corrusca.save(skip_calculate_path=True)
        corruscant = m.OrgUnit(org_unit_type=self.system, parent=corrusca, name="Coruscant System")
        corruscant.save(skip_calculate_path=True)
        jedi_council_corruscant = m.OrgUnit(
            org_unit_type=self.jedi_council, parent=corruscant, name="Corruscant Jedi Council"
        )
        jedi_council_corruscant.save(skip_calculate_path=True)

        self.assertIsNone(corrusca.path)
        self.assertIsNone(corruscant.path)
        self.assertIsNone(jedi_council_corruscant.path)

        # 2 savepoints, 1 regular update, 3 "get children" queries, 1 bulk update
        with self.assertNumQueries(7):
            corrusca.save(update_fields=["path"])

        corruscant.refresh_from_db()
        jedi_council_corruscant.refresh_from_db()

        self.assertEqual(str(corrusca.path), str(corrusca.pk))
        self.assertEqual(str(corruscant.path), f"{corrusca.pk}.{corruscant.pk}")
        self.assertEqual(
            str(jedi_council_corruscant.path), f"{corrusca.pk}.{corruscant.pk}.{jedi_council_corruscant.pk}"
        )

    def test_org_unit_path_does_not_change(self):
        """Updating the "name" property should not result in path change queries"""

        corrusca = m.OrgUnit.objects.create(org_unit_type=self.sector, name="Corrusca Sector")
        corruscant = m.OrgUnit.objects.create(org_unit_type=self.system, parent=corrusca, name="Coruscant System")
        m.OrgUnit.objects.create(org_unit_type=self.jedi_council, parent=corruscant, name="Corruscant Jedi Council")

        corrusca.name = "Corrusca Sector FTW"
        # 2 savepoints, 1 regular update
        with self.assertNumQueries(3):
            corrusca.save()

    def test_org_unit_save_skip_calculate_path(self):
        """If skip_calculate_path is set to True, path should be None, and no transaction should be created"""

        # create
        corrusca = m.OrgUnit(org_unit_type=self.sector, name="Corrusca Sector")
        with self.assertNumQueries(1):
            corrusca.save(skip_calculate_path=True)

        # update
        corrusca.name = "Corrusca Sector FTW"
        with self.assertNumQueries(1):
            corrusca.save(skip_calculate_path=True)

    def test_org_unit_path_does_change(self):
        """Changing the parent should trigger a path update"""

        alderaan = m.OrgUnit.objects.create(org_unit_type=self.sector, name="Alderaan Sector")
        corrusca = m.OrgUnit.objects.create(org_unit_type=self.sector, name="Corrusca Sector")
        corruscant = m.OrgUnit.objects.create(org_unit_type=self.system, parent=alderaan, name="Coruscant System")
        m.OrgUnit.objects.create(org_unit_type=self.jedi_council, parent=corruscant, name="Corruscant Jedi Council")

        corruscant.name = "The awesome Coruscant System"
        corruscant.parent = corrusca

        # 2 savepoints, 1 regular update, 2 children, 1 bulk update
        with self.assertNumQueries(6):
            corruscant.save()

    def test_org_unit_hierarchy_children_descendants(self):
        """Test manager methods: hierarchy(), children() and descendants()."""

        (corrusca, corruscant, first_council, second_council, task_force) = self.create_simple_hierarchy()

        self.assertEqual(5, m.OrgUnit.objects.hierarchy(corrusca).count())
        self.assertEqual(5, m.OrgUnit.objects.hierarchy(m.OrgUnit.objects.filter(name__icontains="corrus")).count())
        self.assertEqual(1, m.OrgUnit.objects.children(corrusca).count())
        self.assertEqual(4, m.OrgUnit.objects.descendants(corrusca).count())

        self.assertEqual(4, m.OrgUnit.objects.hierarchy(corruscant).count())
        self.assertEqual(2, m.OrgUnit.objects.children(corruscant).count())
        self.assertEqual(3, m.OrgUnit.objects.descendants(corruscant).count())

        self.assertEqual(2, m.OrgUnit.objects.hierarchy(first_council).count())
        self.assertEqual(3, m.OrgUnit.objects.hierarchy([first_council, second_council]).count())
        self.assertEqual(1, m.OrgUnit.objects.children(first_council).count())
        self.assertEqual(1, m.OrgUnit.objects.descendants(first_council).count())

        self.assertEqual(1, m.OrgUnit.objects.hierarchy(task_force).count())
        self.assertEqual(0, m.OrgUnit.objects.children(task_force).count())
        self.assertEqual(0, m.OrgUnit.objects.descendants(task_force).count())

        # membership sanity checks
        self.assertIn(first_council, m.OrgUnit.objects.hierarchy(corrusca))
        self.assertNotIn(first_council, m.OrgUnit.objects.children(corrusca))
        self.assertIn(first_council, m.OrgUnit.objects.descendants(corrusca))
        self.assertIn(first_council, m.OrgUnit.objects.hierarchy(corruscant))
        self.assertIn(first_council, m.OrgUnit.objects.children(corruscant))
        self.assertIn(first_council, m.OrgUnit.objects.descendants(corruscant))
        self.assertIn(first_council, m.OrgUnit.objects.hierarchy(first_council))
        self.assertNotIn(first_council, m.OrgUnit.objects.children(first_council))
        self.assertNotIn(first_council, m.OrgUnit.objects.descendants(first_council))
        self.assertNotIn(first_council, m.OrgUnit.objects.hierarchy(second_council))
        self.assertNotIn(first_council, m.OrgUnit.objects.children(second_council))
        self.assertNotIn(first_council, m.OrgUnit.objects.descendants(second_council))
        self.assertNotIn(first_council, m.OrgUnit.objects.hierarchy(task_force))
        self.assertNotIn(first_council, m.OrgUnit.objects.children(task_force))
        self.assertNotIn(first_council, m.OrgUnit.objects.descendants(task_force))

    def create_simple_hierarchy(self):
        corrusca = m.OrgUnit.objects.create(org_unit_type=self.sector, name="Corrusca Sector")
        corruscant = m.OrgUnit.objects.create(org_unit_type=self.system, parent=corrusca, name="Coruscant System")
        first_council = m.OrgUnit.objects.create(
            org_unit_type=self.jedi_council, parent=corruscant, name="First Corruscant Jedi Council"
        )
        second_council = m.OrgUnit.objects.create(
            org_unit_type=self.jedi_council, parent=corruscant, name="Second Corruscant Jedi Council"
        )
        task_force = m.OrgUnit.objects.create(
            org_unit_type=self.jedi_task_force, parent=first_council, name="Jedi Ethics Task Force"
        )
        corrusca.refresh_from_db()
        corruscant.refresh_from_db()
        first_council.refresh_from_db()
        second_council.refresh_from_db()
        task_force.refresh_from_db()

        return corrusca, corruscant, first_council, second_council, task_force


class OrgUnitModelDbTestCase(TestCase):
    """OrgUnit: tests at the database (constraints, ...) level"""

    @classmethod
    def setUpTestData(cls):
        cls.sector = m.OrgUnitType.objects.create(name="Sector", short_name="Sec")
        cls.source = m.DataSource.objects.create(name="source")
        cls.version1 = m.SourceVersion.objects.create(data_source=cls.source, number=1)
        cls.version2 = m.SourceVersion.objects.create(data_source=cls.source, number=2)
        cls.account = m.Account.objects.create(name="a", default_version=cls.version1)

    def activate_constraints(self):
        """Active constraints inside the test, so that it raise in real time

        Kind of a hack but need to check the constraints, otherwise Django only check them
        at teardown, and we can't catch them.

        This will be automatically reversed in teardown. Only tested with postgres
        Note that the transaction will be blocked once an error occur
        """
        for db_name in reversed(self._databases_names()):
            if self._should_check_constraints(connections[db_name]):
                connections[db_name].cursor().execute("SET CONSTRAINTS ALL IMMEDIATE")

    def test_create_same_then_mod_group(self):
        self.activate_constraints()
        orgunit = m.OrgUnit.objects.create(org_unit_type=self.sector, name="OrgUnit", version=self.version1)
        group = m.Group.objects.create(name="group", source_version=self.version1)
        orgunit.groups.set([group])

        group.source_version = self.version2
        with self.assertRaisesMessage(
            InternalError,
            "Constraint violation iaso_group_org_units_same_source_version_constraint",
        ):
            group.save()

    def test_create_same_then_mod_org_unit(self):
        self.activate_constraints()
        orgunit = m.OrgUnit.objects.create(org_unit_type=self.sector, name="OrgUnit", version=self.version1)
        group = m.Group.objects.create(name="group", source_version=self.version1)
        orgunit.groups.set([group])

        orgunit.version = self.version2
        with self.assertRaisesMessage(
            InternalError,
            "Constraint violation iaso_group_org_units_same_source_version_constraint",
        ):
            orgunit.save()

    def test_diff_source_version_fail_at_assign(self):
        self.activate_constraints()
        orgunit = m.OrgUnit.objects.create(org_unit_type=self.sector, name="OrgUnit", version=self.version1)
        group = m.Group.objects.create(name="group", source_version=self.version2)

        with self.assertRaisesMessage(
            InternalError,
            "Constraint violation iaso_group_org_units_same_source_version_constraint",
        ):
            orgunit.groups.set([group])

    # def test_empty_geom(self):
    #     #  regression test for IA-1326
    #     ou = m.OrgUnit.objects.create(name="test", location=Point(float("nan"), float("nan"), z=0))

    #     # DB return an empty 2D point, and not POINT Z EMPTY which is 3D
    #     ous = m.OrgUnit.objects.filter(id=ou.id).extra(select={"raw_location": "ST_AsEWKT(location)"})
    #     breakpoint()
    #     self.assertEqual("SRID=4326;POINT EMPTY", ous.first().raw_location)

    #     ou.refresh_from_db()
    #     ou.name = "test2"
    #     ou.save()

    def test_jsondatastore_extra_fields(self):
        self.activate_constraints()
        orgunit = m.OrgUnit.objects.create(
            org_unit_type=self.sector,
            name="OrgUnit",
            version=self.version1,
        )

        extra_fields = {"population": 1000, "source": "snis"}
        orgunit.set_extra_fields(extra_fields)
        self.assertEqual(orgunit.extra_fields, extra_fields)

        # add more extra fields and update existing ones
        orgunit.set_extra_fields({"population": 2500, "foo": "bar"})
        orgunit.refresh_from_db()
        self.assertEqual(
            orgunit.extra_fields,
            {"population": 2500, "source": "snis", "foo": "bar"},
        )
