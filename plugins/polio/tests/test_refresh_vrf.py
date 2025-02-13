from datetime import datetime
from iaso import models as m
from iaso.test import APITestCase
from iaso.models.base import RUNNING, KILLED, SUCCESS, SKIPPED
from iaso.models.json_config import Config
from unittest.mock import patch
from plugins.polio.tasks.api.refresh_vrf_dashboard_data import VRF_CONFIG_SLUG, VRF_TASK_NAME, RefreshVrfDataViewset


class RefreshVrfDataTestCase(APITestCase):
    @classmethod
    def setUp(cls):
        cls.url = "/api/polio/tasks/refreshvrf/"
        cls.account = account = m.Account.objects.create(name="test account")
        cls.user = cls.create_user_with_profile(username="test user", account=account, permissions=["iaso_polio"])

        cls.external_task1 = m.Task.objects.create(
            status=RUNNING, account=account, launcher=cls.user, name="external task 1", external=True
        )
        cls.external_task2 = m.Task.objects.create(
            status=RUNNING, account=account, launcher=cls.user, name="external task 2", external=True
        )
        cls.project = m.Project.objects.create(name="Polio", app_id="polio.rapid.outbreak.taskforce", account=account)
        cls.data_source = m.DataSource.objects.create(name="Default source")
        cls.data_source.projects.add(cls.project)
        cls.data_source.save()
        cls.source_version = m.SourceVersion.objects.create(data_source=cls.data_source, number=1)
        cls.account.default_version = cls.source_version
        cls.account.save()

        cls.task1 = m.Task.objects.create(
            status=RUNNING,
            account=account,
            launcher=cls.user,
            name=VRF_CONFIG_SLUG,
            started_at=datetime.now(),
            external=True,
        )
        cls.task2 = m.Task.objects.create(
            status=RUNNING, account=account, launcher=cls.user, name="task 2", external=True
        )

        cls.json_config = {
            "pipeline": "pipeline",
            "openhexa_url": "https://yippie.openhexa.xyz/",
            "openhexa_token": "token",
            "pipeline_version": 1,
            "oh_pipeline_target": "staging",
        }
        cls.vrf_config = Config.objects.create(slug=VRF_CONFIG_SLUG, content=cls.json_config)

    def mock_openhexa_call_success(self, slug=None, config=None, id_field=None, task_id=None):
        return SUCCESS

    def mock_openhexa_call_skipped(self, slug=None, config=None, id_field=None, task_id=None):
        return SKIPPED

    def mock_openhexa_call_running(self, slug=None, config=None, id_field=None, task_id=None):
        return RUNNING

    def test_no_auth_needed(self):
        user_no_perm = self.create_user_with_profile(username="test user2", account=self.account, permissions=[])
        self.client.force_authenticate(user_no_perm)
        response = self.client.get(
            self.url,
            format="json",
        )
        self.assertJSONResponse(response, 200)

    @patch.object(RefreshVrfDataViewset, "launch_task", mock_openhexa_call_running)
    def test_create_external_task(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            self.url,
        )
        response = self.assertJSONResponse(response, 200)
        task = response["task"]
        self.assertEqual(task["status"], RUNNING)
        self.assertEqual(task["launcher"]["username"], self.user.username)
        self.assertEqual(task["name"], VRF_TASK_NAME)

    @patch.object(RefreshVrfDataViewset, "launch_task", mock_openhexa_call_skipped)
    def test_create_external_task_pipeline_already_running(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            self.url,
        )
        response = self.assertJSONResponse(response, 200)
        task = response["task"]
        self.assertEqual(task["status"], SKIPPED)
        self.assertEqual(task["launcher"]["username"], self.user.username)
        self.assertEqual(task["name"], VRF_TASK_NAME)

    @patch.object(RefreshVrfDataViewset, "launch_task", mock_openhexa_call_running)
    def test_patch_external_task(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            self.url,
        )
        response = self.assertJSONResponse(response, 200)
        task = response["task"]
        task_id = task["id"]
        self.assertEqual(task["status"], RUNNING)
        self.assertEqual(task["progress_value"], 0)
        self.assertEqual(task["end_value"], 0)

        response = self.client.patch(
            f"{self.url}{task_id}/", format="json", data={"status": SUCCESS, "progress_value": 21}
        )
        response = self.assertJSONResponse(response, 200)
        task = response
        self.assertEqual(task["id"], task_id)
        self.assertEqual(task["status"], SUCCESS)
        self.assertEqual(task["progress_value"], 21)
        self.assertEqual(task["end_value"], 0)

    @patch.object(RefreshVrfDataViewset, "launch_task", mock_openhexa_call_running)
    def test_kill_external_task(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            self.url,
        )
        response = self.assertJSONResponse(response, 200)
        task = response["task"]
        task_id = task["id"]
        print("Task", task)
        self.assertEqual(task["status"], RUNNING)

        response = self.client.patch(
            f"{self.url}{task_id}/",
            format="json",
            data={
                "should_be_killed": True,
            },
        )
        response = self.assertJSONResponse(response, 200)
        task = response
        self.assertEqual(task["id"], task_id)
        self.assertEqual(task["status"], KILLED)
