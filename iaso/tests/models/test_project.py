from iaso import models as m
from iaso.test import TestCase


class ProjectModelTestCase(TestCase):
    """
    Test Project model.
    """

    @classmethod
    def setUpTestData(cls):
        cls.global_health = m.Account.objects.create(name="Global Health Initiative")
        cls.other_account = m.Account.objects.create(name="Other Account")

        cls.project_1 = m.Project.objects.create(name="Project 1", app_id="org.ghi.p1", account=cls.global_health)
        cls.project_2 = m.Project.objects.create(name="Project 2", app_id="org.ghi.p2", account=cls.global_health)
        cls.project_3 = m.Project.objects.create(name="Project 3", app_id="org.oa.p3", account=cls.other_account)

        cls.jane = cls.create_user_with_profile(username="jane", account=cls.global_health)
        cls.jane.iaso_profile.projects.set([cls.project_1, cls.project_2])

        cls.john = cls.create_user_with_profile(username="john", account=cls.global_health)
        cls.john.iaso_profile.projects.set([cls.project_1])

        cls.jim = cls.create_user_with_profile(username="jim", account=cls.global_health)

        cls.user_without_profile = m.User.objects.create(username="foo")

    def test_filter_on_user_projects(self):
        total_projects = m.Project.objects.count()
        self.assertEqual(total_projects, 3)

        jane_projects = m.Project.objects.filter_on_user_projects(user=self.jane)
        self.assertEqual(jane_projects.count(), 2)
        self.assertIn(self.project_1, jane_projects)
        self.assertIn(self.project_2, jane_projects)

        john_projects = m.Project.objects.filter_on_user_projects(user=self.john)
        self.assertEqual(john_projects.count(), 1)
        self.assertIn(self.project_1, john_projects)

        jim_projects = m.Project.objects.filter_on_user_projects(user=self.jim)
        self.assertEqual(jim_projects.count(), total_projects)

        user_without_profile_projects = m.Project.objects.filter_on_user_projects(user=self.user_without_profile)
        self.assertEqual(user_without_profile_projects.count(), total_projects)
