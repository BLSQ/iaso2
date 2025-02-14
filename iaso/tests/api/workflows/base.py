from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.core.files import File
from django.core.files.uploadedfile import UploadedFile
from django.utils.timezone import now

from iaso import models as m
from iaso.models import Workflow, WorkflowVersion
from iaso.models.workflow import WorkflowVersionsStatus, WorkflowChange, WorkflowFollowup
from iaso.test import APITestCase


class BaseWorkflowsAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.now = now()

        blue_adults = m.Account.objects.create(name="Blue Adults")
        blue_children = m.Account.objects.create(name="Blue Children")

        cls.anon = AnonymousUser()

        cls.blue_adult_1 = cls.create_user_with_profile(
            username="blue_adult_1", account=blue_adults, permissions=["iaso_workflows"]
        )

        cls.blue_child_1 = cls.create_user_with_profile(
            username="blue_child_1",
            account=blue_children,
            permissions=["iaso_workflows"],
        )

        # He doesn't have permissions
        cls.blue_adult_np = cls.create_user_with_profile(username="blue_adult_np", account=blue_adults)

        cls.project_blue_adults = m.Project.objects.create(
            name="Blue Adults Project",
            app_id="blue.adults.project",
            account=blue_adults,
        )

        cls.project_blue_adults_2 = m.Project.objects.create(
            name="Blue Adults Project_2",
            app_id="blue.adults.project_2",
            account=blue_adults,
        )

        cls.project_blue_childrens = m.Project.objects.create(
            name="Blue Childrens Project",
            app_id="blue.childrens.project",
            account=blue_children,
        )

        cls.form_adults_blue = m.Form.objects.create(
            name="Blue Adults Form", form_id="adults_form_blue", created_at=cls.now
        )

        cls.form_adults_blue_2 = m.Form.objects.create(
            name="Blue Adults Form 2", form_id="adults_form_blue_2", created_at=cls.now
        )

        cls.form_adults_blue_3 = m.Form.objects.create(
            name="Blue Adults Form 3", form_id="adults_form_blue_3", created_at=cls.now
        )

        cls.form_adults_blue_4 = m.Form.objects.create(
            name="Blue Adults Form 4", form_id="adults_form_blue_4", created_at=cls.now
        )

        form_adults_blue_mock = mock.MagicMock(spec=File)
        form_adults_blue_mock.name = "test.xml"
        with open("iaso/tests/fixtures/form_test_workflow.xlsx", "rb") as xls_file:
            cls.form_adults_blue.form_versions.create(
                file=form_adults_blue_mock, xls_file=UploadedFile(xls_file), version_id="2020022401"
            )

        cls.form_adults_blue.update_possible_fields()
        cls.form_adults_blue.save()

        form_adults_blue_2_mock = mock.MagicMock(spec=File)
        form_adults_blue_2_mock.name = "test.xml"
        with open("iaso/tests/fixtures/form_test_workflow.xlsx", "rb") as xls_file:
            cls.form_adults_blue_2.form_versions.create(
                file=form_adults_blue_2_mock, xls_file=UploadedFile(xls_file), version_id="2020022301"
            )

        cls.form_adults_blue_2.update_possible_fields()
        cls.form_adults_blue_2.save()

        cls.form_children_blue = m.Form.objects.create(
            name="Blue Children Form", form_id="children_form_blue", created_at=cls.now
        )

        cls.project_blue_childrens.forms.add(cls.form_children_blue)

        cls.project_blue_adults.forms.add(cls.form_adults_blue)
        cls.project_blue_adults.forms.add(cls.form_adults_blue_2)
        cls.project_blue_adults.save()

        cls.project_blue_adults_2.forms.add(cls.form_adults_blue_3)
        cls.project_blue_adults_2.forms.add(cls.form_adults_blue_4)
        cls.project_blue_adults_2.save()

        cls.et_children_blue = m.EntityType.objects.create(
            name="Children of Blue",
            created_at=cls.now,
            account=blue_children,
            reference_form=cls.form_children_blue,
        )

        cls.workflow_et_children_blue = Workflow.objects.create(entity_type=cls.et_children_blue)

        cls.workflow_version_et_children_blue = WorkflowVersion.objects.create(
            workflow=cls.workflow_et_children_blue,
            name="workflow_version_et_children_blue V1",
            status=WorkflowVersionsStatus.DRAFT,
        )

        cls.et_adults_blue = m.EntityType.objects.create(
            name="Adults of Blue",
            created_at=cls.now,
            account=blue_adults,
            reference_form=cls.form_adults_blue,
        )

        cls.et_adults_blue_2 = m.EntityType.objects.create(
            name="Adults of Blue 2",
            created_at=cls.now,
            account=blue_adults,
            reference_form=cls.form_adults_blue,
        )

        cls.et_adults_blue_3 = m.EntityType.objects.create(
            name="Adults of Blue 3",
            created_at=cls.now,
            account=blue_adults,
            reference_form=cls.form_adults_blue_3,
        )

        # This is added to check if the error on get returning more than one EntityType occurs again(WC2-500)
        different_account = m.Account.objects.create(name="Different Account")
        cls.et_adults_blue_2_same_name_different_account = m.EntityType.objects.create(
            name="Adults of Blue 2",
            created_at=cls.now,
            account=different_account,
            reference_form=cls.form_adults_blue,
        )

        cls.workflow_et_adults_blue = Workflow.objects.create(entity_type=cls.et_adults_blue)

        cls.workflow_version_et_adults_blue = WorkflowVersion.objects.create(
            workflow=cls.workflow_et_adults_blue,
            name="workflow_version_et_adults_blue V1",
            status=WorkflowVersionsStatus.PUBLISHED,
        )
        cls.workflow_version_et_adults_blue_draft_2 = WorkflowVersion.objects.create(
            workflow=cls.workflow_et_adults_blue,
            name="workflow_version_et_adults_blue V2 draft",
            status=WorkflowVersionsStatus.DRAFT,
        )

        cls.workflow_version_et_adults_blue_draft = WorkflowVersion.objects.create(
            workflow=cls.workflow_et_adults_blue,
            name="workflow_version_et_adults_blue V2",
            status=WorkflowVersionsStatus.DRAFT,
        )

        cls.workflow_et_adults_blue_with_followups_and_changes = Workflow.objects.create(
            entity_type=cls.et_adults_blue_2
        )

        cls.workflow_version_et_adults_blue_with_followups_and_changes = WorkflowVersion.objects.create(
            workflow=cls.workflow_et_adults_blue_with_followups_and_changes,
            name="workflow_et_adults_blue_with V1",
            status=WorkflowVersionsStatus.DRAFT,
        )

        WorkflowChange.objects.create(
            form=cls.form_adults_blue_2,
            workflow_version=cls.workflow_version_et_adults_blue_with_followups_and_changes,
            mapping={"mon_champ": "mon_champ"},
        )

        followup = WorkflowFollowup.objects.create(
            order=1,
            condition={"==": [1, 1]},
            workflow_version=cls.workflow_version_et_adults_blue_with_followups_and_changes,
        )

        followup.forms.add(cls.form_adults_blue_2)

        cls.workflow_version_full_published = WorkflowVersion.objects.create(
            workflow=cls.workflow_et_adults_blue_with_followups_and_changes,
            name="workflow_et_adults_blue_with V2",
            status=WorkflowVersionsStatus.PUBLISHED,
        )

        WorkflowChange.objects.create(
            form=cls.form_adults_blue_2,
            workflow_version=cls.workflow_version_full_published,
            mapping={"mon_champ": "mon_champ"},
        )

        followup2 = WorkflowFollowup.objects.create(
            order=1,
            condition={"==": [1, 1]},
            workflow_version=cls.workflow_version_et_adults_blue_with_followups_and_changes,
        )

        followup2.forms.add(cls.form_adults_blue_2)

        cls.workflow_et_adults_blue_2 = Workflow.objects.create(entity_type=cls.et_adults_blue_3)

        cls.workflow_version_et_adults_blue_2 = WorkflowVersion.objects.create(
            workflow=cls.workflow_et_adults_blue_2,
            name="workflow_et_adults_blue_2 V1",
            status=WorkflowVersionsStatus.PUBLISHED,
        )

        WorkflowChange.objects.create(
            form=cls.form_adults_blue_4,
            workflow_version=cls.workflow_version_et_adults_blue_2,
            mapping={"mon_champ": "mon_champ"},
        )

        followup_3 = WorkflowFollowup.objects.create(
            order=1,
            condition={"==": [1, 1]},
            workflow_version=cls.workflow_version_et_adults_blue_2,
        )
        followup_3.forms.add(cls.form_adults_blue_4)
