from iaso import models as m
from iaso.test import TestCase


class FormModelTestCase(TestCase):
    """
    Test Form model.
    """

    @classmethod
    def setUpTestData(cls):
        cls.health_account = m.Account.objects.create(name="Global Health Initiative")

        cls.project_1 = m.Project.objects.create(name="Project 1", app_id="org.ghi.p1", account=cls.health_account)
        cls.project_2 = m.Project.objects.create(name="Project 2", app_id="org.ghi.p2", account=cls.health_account)

        cls.form_1 = m.Form.objects.create(name="Form 1")
        cls.form_2 = m.Form.objects.create(name="Form 2")
        cls.form_3 = m.Form.objects.create(name="Form 3")
        cls.form_4 = m.Form.objects.create(name="Form 4")

        cls.project_1.forms.set([cls.form_1, cls.form_2])
        cls.project_2.forms.set([cls.form_3, cls.form_4])

        cls.jane = cls.create_user_with_profile(username="jane", account=cls.health_account)
        cls.jane.iaso_profile.projects.set([cls.project_1, cls.project_2])

        cls.john = cls.create_user_with_profile(username="john", account=cls.health_account)
        cls.john.iaso_profile.projects.set([cls.project_1])

        cls.jim = cls.create_user_with_profile(username="jim", account=cls.health_account)

        cls.user_without_profile = m.User.objects.create(username="foo")

    def test_filter_on_user_projects(self):
        total_forms = m.Form.objects.count()
        self.assertEqual(total_forms, 4)

        jane_forms = m.Form.objects.filter_on_user_projects(user=self.jane)
        self.assertEqual(jane_forms.count(), 4)
        self.assertIn(self.form_1, jane_forms)
        self.assertIn(self.form_2, jane_forms)
        self.assertIn(self.form_3, jane_forms)
        self.assertIn(self.form_4, jane_forms)

        john_forms = m.Form.objects.filter_on_user_projects(user=self.john)
        self.assertEqual(john_forms.count(), 2)
        self.assertIn(self.form_1, john_forms)
        self.assertIn(self.form_2, john_forms)

        jim_forms = m.Form.objects.filter_on_user_projects(user=self.jim)
        self.assertEqual(jim_forms.count(), total_forms)

        user_without_profile_projects = m.Form.objects.filter_on_user_projects(user=self.user_without_profile)
        self.assertEqual(user_without_profile_projects.count(), total_forms)
