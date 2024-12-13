from collections import OrderedDict
from enum import Enum

from django.db import transaction
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from iaso.api.common import DynamicFieldsModelSerializer
from iaso.models.microplanning import Team
from plugins.polio.api.shared_serializers import UserSerializer

from ..models import Campaign, Round
from .models import (
    BudgetProcess,
    BudgetStep,
    BudgetStepFile,
    BudgetStepLink,
    get_workflow,
    model_field_exists,
    send_budget_mails,
)
from .workflow import Category, can_user_transition, effective_teams, next_transitions


class TransitionSerializer(serializers.Serializer):
    key = serializers.CharField()
    # https://github.com/typeddjango/djangorestframework-stubs/issues/78 bug in mypy remove in future
    label = serializers.CharField()  # type: ignore
    help_text = serializers.CharField()  # type: ignore
    allowed = serializers.BooleanField()
    reason_not_allowed = serializers.CharField(required=False)
    required_fields = serializers.ListField(child=serializers.CharField())
    displayed_fields = serializers.ListField(child=serializers.CharField())
    # Note : implemented as a Css class in the frontend. Color of the button for approval
    color = serializers.ChoiceField(choices=["primary", "green", "red"], required=False)
    emails_destination_team_ids = serializers.ListField(child=serializers.IntegerField(), required=False)


class NestedTransitionSerializer(TransitionSerializer):
    key = serializers.CharField()
    # https://github.com/typeddjango/djangorestframework-stubs/issues/78 bug in mypy remove in future
    label = serializers.CharField()  # type: ignore


class NodeSerializer(serializers.Serializer):
    key = serializers.CharField()
    # https://github.com/typeddjango/djangorestframework-stubs/issues/78 bug in mypy remove in future
    label = serializers.CharField()  # type: ignore


class WorkflowSerializer(serializers.Serializer):
    states = NodeSerializer(many=True, source="nodes")


class CategoryItemSerializer(serializers.Serializer):
    # https://github.com/typeddjango/djangorestframework-stubs/issues/78 bug in mypy remove in future
    label = serializers.CharField()  # type: ignore
    performed_by = UserSerializer(required=False)
    performed_at = serializers.DateTimeField(required=False)
    step_id = serializers.IntegerField(required=False)
    skipped = serializers.BooleanField(required=False)
    cancelled = serializers.BooleanField(required=False)


class CategorySerializer(serializers.Serializer):
    key = serializers.CharField()
    # https://github.com/typeddjango/djangorestframework-stubs/issues/78 bug in mypy remove in future
    label = serializers.CharField()  # type: ignore
    color = serializers.CharField(help_text="Color completed according to the progress")
    items = CategoryItemSerializer(many=True)
    completed = serializers.BooleanField(help_text="Every step in the category is done")
    active = serializers.BooleanField(help_text="Category has been started")


class TimelineSerializer(serializers.Serializer):
    categories = CategorySerializer(many=True)


class AvailableRoundsSerializer(serializers.Serializer):
    campaign_id = serializers.UUIDField()
    budget_process_id = serializers.IntegerField()


class BudgetProcessNestedRoundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Round
        fields = [
            "id",
            "number",
            "cost",
            "target_population",
        ]


class BudgetProcessWriteRoundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Round
        fields = [
            "id",
            "cost",
        ]
        extra_kwargs = {"id": {"read_only": False}}


class BudgetProcessWriteSerializer(serializers.ModelSerializer):
    """
    Create or update a `BudgetProcess` that is linked to one (or more) `Round`(s).
    """

    created_by = UserSerializer(read_only=True)
    rounds = BudgetProcessWriteRoundSerializer(many=True)

    class Meta:
        model = BudgetProcess
        fields = [
            "id",  # Read only.
            "created_by",  # Read only.
            "created_at",  # Read only.
            "rounds",
            "ra_completed_at_WFEDITABLE",
            "who_sent_budget_at_WFEDITABLE",
            "unicef_sent_budget_at_WFEDITABLE",
            "gpei_consolidated_budgets_at_WFEDITABLE",
            "submitted_to_rrt_at_WFEDITABLE",
            "feedback_sent_to_gpei_at_WFEDITABLE",
            "re_submitted_to_rrt_at_WFEDITABLE",
            "submitted_to_orpg_operations1_at_WFEDITABLE",
            "feedback_sent_to_rrt1_at_WFEDITABLE",
            "re_submitted_to_orpg_operations1_at_WFEDITABLE",
            "submitted_to_orpg_wider_at_WFEDITABLE",
            "submitted_to_orpg_operations2_at_WFEDITABLE",
            "feedback_sent_to_rrt2_at_WFEDITABLE",
            "re_submitted_to_orpg_operations2_at_WFEDITABLE",
            "submitted_for_approval_at_WFEDITABLE",
            "feedback_sent_to_orpg_operations_unicef_at_WFEDITABLE",
            "feedback_sent_to_orpg_operations_who_at_WFEDITABLE",
            "approved_by_who_at_WFEDITABLE",
            "approved_by_unicef_at_WFEDITABLE",
            "approved_at_WFEDITABLE",
            "approval_confirmed_at_WFEDITABLE",
            "payment_mode",
            "district_count",
            "who_disbursed_to_co_at",
            "who_disbursed_to_moh_at",
            "unicef_disbursed_to_co_at",
            "unicef_disbursed_to_moh_at",
            "no_regret_fund_amount",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "created_by": {"read_only": True},
            "created_at": {"read_only": True},
        }

    def validate_rounds(self, submitted_rounds: list[OrderedDict]) -> list[OrderedDict]:
        request = self.context["request"]
        is_new = self.instance is None
        round_ids = [round_dict.get("id") for round_dict in submitted_rounds]

        rounds = Round.objects.filter(id__in=round_ids).select_related("campaign", "budget_process")

        valid_rounds_ids = Campaign.objects.filter_for_user(request.user).values_list("rounds", flat=True)
        invalid_round_ids = [round.id for round in rounds if round.id not in valid_rounds_ids]
        if invalid_round_ids:
            raise serializers.ValidationError(
                f"The user does not have the permissions for rounds: {invalid_round_ids}."
            )

        if is_new:
            already_linked_round_ids = [round.id for round in rounds if round.budget_process]
            if already_linked_round_ids:
                raise serializers.ValidationError(
                    f"A BudgetProcess already exists for rounds: {already_linked_round_ids}."
                )

        rounds_campaigns = {round.campaign_id for round in rounds}
        if len(rounds_campaigns) > 1:
            raise serializers.ValidationError("Rounds must be from the same campaign.")

        return submitted_rounds

    def handle_rounds(self, budget_process: BudgetProcess, rounds_data: dict) -> None:
        for round_data in rounds_data:
            round_id = round_data.get("id")
            if round_id:
                round_instance = Round.objects.get(id=round_id)
                round_serializer = BudgetProcessWriteRoundSerializer(round_instance, data=round_data, partial=True)
                if round_serializer.is_valid():
                    round_serializer.save(budget_process=budget_process)

    def create(self, validated_data: dict) -> BudgetProcess:
        request = self.context["request"]
        rounds_data = validated_data.pop("rounds", [])
        validated_data["created_by"] = request.user
        budget_process = super().create(validated_data)
        self.handle_rounds(budget_process, rounds_data)
        return budget_process

    def update(self, budget_process: BudgetProcess, validated_data: dict) -> BudgetProcess:
        rounds_data = validated_data.pop("rounds", [])

        budget_process = super().update(budget_process, validated_data)
        existing_round_ids = set(budget_process.rounds.values_list("id", flat=True))
        new_round_ids = {round_data["id"] for round_data in rounds_data if "id" in round_data}

        # should we also empty cost?
        rounds_to_unlink = existing_round_ids - new_round_ids
        # Unlink old rounds.
        if rounds_to_unlink:
            Round.objects.filter(id__in=rounds_to_unlink).update(budget_process=None)
        # Link new rounds.
        self.handle_rounds(budget_process, rounds_data)
        return budget_process


class BudgetProcessSerializer(DynamicFieldsModelSerializer, serializers.ModelSerializer):
    class Meta:
        model = BudgetProcess
        fields = [
            "created_at",
            "id",
            "campaign_id",  # Added via `annotate`.
            "obr_name",  # Added via `annotate`.
            "country_name",  # Added via `annotate`.
            "rounds",
            "current_state",
            "updated_at",
            "possible_states",
            "next_transitions",
            "possible_transitions",
            "timeline",
            "ra_completed_at_WFEDITABLE",
            "who_sent_budget_at_WFEDITABLE",
            "unicef_sent_budget_at_WFEDITABLE",
            "gpei_consolidated_budgets_at_WFEDITABLE",
            "submitted_to_rrt_at_WFEDITABLE",
            "feedback_sent_to_gpei_at_WFEDITABLE",
            "re_submitted_to_rrt_at_WFEDITABLE",
            "submitted_to_orpg_operations1_at_WFEDITABLE",
            "feedback_sent_to_rrt1_at_WFEDITABLE",
            "re_submitted_to_orpg_operations1_at_WFEDITABLE",
            "submitted_to_orpg_wider_at_WFEDITABLE",
            "submitted_to_orpg_operations2_at_WFEDITABLE",
            "feedback_sent_to_rrt2_at_WFEDITABLE",
            "re_submitted_to_orpg_operations2_at_WFEDITABLE",
            "submitted_for_approval_at_WFEDITABLE",
            "feedback_sent_to_orpg_operations_unicef_at_WFEDITABLE",
            "feedback_sent_to_orpg_operations_who_at_WFEDITABLE",
            "approved_by_who_at_WFEDITABLE",
            "approved_by_unicef_at_WFEDITABLE",
            "approved_at_WFEDITABLE",
            "approval_confirmed_at_WFEDITABLE",
            "payment_mode",
            "district_count",
            "who_disbursed_to_co_at",
            "who_disbursed_to_moh_at",
            "unicef_disbursed_to_co_at",
            "unicef_disbursed_to_moh_at",
            "no_regret_fund_amount",
            "has_data_in_budget_tool",
        ]
        default_fields = [
            "created_at",
            "id",
            "campaign_id",
            "obr_name",
            "country_name",
            "rounds",
            "current_state",
            "updated_at",
        ]

    campaign_id = serializers.UUIDField()
    obr_name = serializers.CharField()
    country_name = serializers.CharField()
    rounds = BudgetProcessNestedRoundSerializer(many=True)
    current_state = serializers.SerializerMethodField()
    possible_states = serializers.SerializerMethodField()
    possible_transitions = serializers.SerializerMethodField()
    timeline = serializers.SerializerMethodField()
    next_transitions = serializers.SerializerMethodField()
    has_data_in_budget_tool = serializers.SerializerMethodField(read_only=True)

    def get_has_data_in_budget_tool(self, budget_process: BudgetProcess):
        return budget_process.budget_steps.count() > 0

    def get_current_state(self, budget_process: BudgetProcess):
        workflow = get_workflow()
        try:
            node = workflow.get_node_by_key(budget_process.current_state_key)
        except:
            return {
                "key": budget_process.current_state_key,
                "label": budget_process.current_state_key,
            }
        else:
            return {
                "key": budget_process.current_state_key,
                "label": node.label,
            }

    @swagger_serializer_method(serializer_or_field=TransitionSerializer(many=True))
    def get_next_transitions(self, budget_process: BudgetProcess):
        # // get transition from workflow engine.
        workflow = get_workflow()
        campaign = budget_process.rounds.first().campaign
        transitions = next_transitions(workflow.transitions, budget_process.current_state_key)
        user = self.context["request"].user
        for transition in transitions:
            allowed = can_user_transition(transition, user, campaign)
            transition.allowed = allowed
            if not allowed:
                if not effective_teams(campaign, transition.teams_ids_can_transition):
                    reason = "No team configured for this country and transition"
                else:
                    reason = "User doesn't have permission"
                transition.reason_not_allowed = reason

            # FIXME: filter on effective teams, need campaign
            teams = []
            for _, teams_ids in transition.emails_to_send:
                teams += effective_teams(campaign, teams_ids).values_list("id", flat=True)
            transition.emails_destination_team_ids = set(teams)

        return TransitionSerializer(transitions, many=True).data

    # this is used for filter dropdown
    @swagger_serializer_method(serializer_or_field=NodeSerializer(many=True))
    def get_possible_states(self, _budget_process: BudgetProcess):
        workflow = get_workflow()
        nodes = workflow.nodes
        return NodeSerializer(nodes, many=True).data

    # this is used for filter dropdown
    @swagger_serializer_method(serializer_or_field=TransitionSerializer(many=True))
    def get_possible_transitions(self, _budget_process: BudgetProcess):
        workflow = get_workflow()
        transitions = workflow.transitions
        return NestedTransitionSerializer(transitions, many=True).data

    @swagger_serializer_method(serializer_or_field=TimelineSerializer())
    def get_timeline(self, budget_process: BudgetProcess):
        """Represent the progression of the budget process, per category

        State/Nodes are stored in category.
        For each category, we return a merge between the Step leading to that node and the node that we still need to visit
        (marked as mandatory).

        So you will get something like
        CategoryA:
           NodeA : Performed by Xavier on 1 Jan
           NodeB : Performed by Olivier on 2 Feb
           NodeC : to do

        We also return a color to mark the progress in each category. In the future we may want to modulate this
        color according to the delay.

        We may want to cache this in the future because this a bit of calculation, and only change when a step is done,
        but it is not critical for now as we only query one campaign at the time in the current design.

        """
        workflow = get_workflow()
        r = []
        c: Category
        steps = list(budget_process.budget_steps.filter(deleted_at__isnull=True).order_by("created_at"))

        override_steps = list(
            budget_process.budget_steps.filter(deleted_at__isnull=True)
            .filter(transition_key="override")
            .order_by("created_at")
        )
        all_nodes = workflow.nodes

        for c in workflow.categories:
            items = []
            node_dict = {node.key: node for node in c.nodes}
            node_passed_by = set()  # Keys
            node_remaining = set()
            step: BudgetStep
            for step in steps:
                to_node_key = step.node_key_to
                # mitigation for old steps with don't have node_key_to
                if not step.node_key_to:
                    if step.transition_key not in workflow.transitions_dict:
                        continue
                    transition = workflow.transitions_dict[step.transition_key]
                    to_node_key = transition.to_node
                    # if step.transition_key == "override"
                    # we need to access the actual step to get the to_node_key, as the one in the workflow is generic and not to be used

                if to_node_key in node_dict.keys():
                    # If this is in the category
                    node = node_dict[to_node_key]
                    for other_key in node.mark_nodes_as_completed:
                        if other_key not in node_passed_by:
                            other_node = node_dict.get(other_key)
                            items.append(
                                {
                                    "label": other_node.label,
                                    "performed_by": step.created_by,
                                    "performed_at": step.created_at,
                                    "step_id": step.id,
                                    "order": other_node.order,
                                    "key": other_node.key,
                                    "mandatory": other_node.mandatory,
                                }
                            )
                            node_passed_by.add(other_key)

                    items.append(
                        {
                            "label": node.label,
                            "performed_by": step.created_by,
                            "performed_at": step.created_at,
                            "step_id": step.id,
                            "order": node.order,
                            "key": node.key,
                            "mandatory": node.mandatory,
                        }
                    )
                    node_passed_by.add(to_node_key)
            for node in c.nodes:  # Node are already sorted
                if not node.mandatory:
                    continue
                if node.key in node_passed_by:
                    continue
                node_remaining.add(node.key)
                items.append(
                    {
                        "label": node.label,
                        "order": node.order,
                        "key": node.key,
                        "mandatory": node.mandatory,
                    }
                )
            r.append(
                {
                    "label": c.label,
                    "key": c.key,
                    "items": items,
                }
            )

        override_step: BudgetStep
        for override_step in override_steps:
            start_node_key = override_step.node_key_from
            destination_node_key = override_step.node_key_to
            # TODO check if list contains one and only one element
            start_node_list = [node for node in all_nodes if node.key == start_node_key]
            start_node = start_node_list[0]
            start_position = start_node.order
            destination_node_list = [node for node in all_nodes if node.key == destination_node_key]
            destination_node = destination_node_list[0]  # This is buggy with the latest config  migration
            destination_position = destination_node.order
            is_skipping = destination_position >= start_position
            reference_date = override_step.created_at
            for section in r:
                for item in section["items"]:
                    if reference_date >= item.get(
                        "performed_at", reference_date
                    ):  # I think using reference date wold create problems with overrides that don't happen on the same day
                        item_order = item["order"]
                        if (
                            is_skipping
                            and item_order > start_position
                            and item_order < destination_position
                            and not item.get("step_id", None)
                        ):
                            item["skipped"] = True
                            item["cancelled"] = False
                        # This is an edge case for when 2 steps have the same order (ie: have to done at the same time,
                        # but with no determined priority, eg: UNICEF Co sends budget and WHO CO sends budget)
                        # We then add a check on the label.
                        elif (
                            is_skipping
                            and item_order >= start_position
                            and item_order < destination_position
                            and item["label"] != start_node.label
                            and not item.get("step_id", None)
                        ):
                            item["skipped"] = True
                            item["cancelled"] = False
                        elif item_order <= start_position and item_order > destination_position and not is_skipping:
                            if item.get("skipped", False) and not item.get("step_id", None):
                                item["cancelled"] = False
                                item["skipped"] = False
                            else:
                                item["skipped"] = False
                                item["cancelled"] = True

        for index, section in enumerate(r):
            mandatory_nodes = list(filter(lambda node: node.mandatory == True, workflow.categories[index].nodes))
            mandatory_nodes_passed = list(filter(lambda x: x.get("mandatory") == True, section["items"]))
            uncancelled_mandatory_nodes_passed = list(
                filter(
                    lambda i: i.get("step_id", None) or i.get("skipped", False),
                    list(filter(lambda i: i.get("cancelled", False) != True, mandatory_nodes_passed)),
                )
            )

            uncancelled_mandatory_nodes_labels = []
            for uncancelled_node in uncancelled_mandatory_nodes_passed:
                uncancelled_mandatory_nodes_labels.append(uncancelled_node["label"])
            unique_nodes_passed = set(uncancelled_mandatory_nodes_labels)
            if len(unique_nodes_passed) == len(mandatory_nodes):
                section["completed"] = True
                section["active"] = False
                section["color"] = "green"
            elif len(unique_nodes_passed) > 0:
                section["completed"] = False
                section["active"] = True
                section["color"] = "yellow"
            else:
                section["completed"] = False
                section["active"] = False
                section["color"] = "grey"

        return TimelineSerializer({"categories": r}).data


class TransitionError(Enum):
    INVALID_TRANSITION = "invalid_transition"
    NOT_ALLOWED = "user_not_allowed"
    MISSING_FIELD = "missing_field"


class BudgetLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetStepLink
        fields = [
            "id",
            "url",
            "alias",
        ]


class TransitionToSerializer(serializers.Serializer):
    transition_key = serializers.CharField()
    budget_process = serializers.PrimaryKeyRelatedField(queryset=BudgetProcess.objects.all())
    comment = serializers.CharField(required=False)
    files = serializers.ListField(child=serializers.FileField(), required=False)
    links = serializers.JSONField(required=False)
    amount = serializers.FloatField(required=False)

    def validate(self, attrs):
        return attrs

    def validate_links(self, value):
        return value

    def save(self, **kwargs):
        data = self.validated_data
        budget_process: BudgetProcess = data["budget_process"]
        campaign: Campaign = budget_process.rounds.first().campaign
        user = self.context["request"].user
        transition_key = data["transition_key"]

        workflow = get_workflow()

        n_transitions = next_transitions(workflow.transitions, budget_process.current_state_key)
        transitions = [t for t in n_transitions if t.key == transition_key]
        if not transitions:
            raise serializers.ValidationError(
                {
                    "transition_key": [
                        TransitionError.INVALID_TRANSITION,
                        f"Valid transitions: {[t.key for t in n_transitions]}",
                    ]
                }
            )
        transition = transitions[0]

        if not can_user_transition(transition, user, campaign):
            raise serializers.ValidationError({"transition_key": [TransitionError.NOT_ALLOWED]})

        for field in transition.required_fields:
            if field == "attachments":
                if len(data.get("files", [])) < 1 and len(data.get("links", [])) < 1:
                    raise Exception(TransitionError.MISSING_FIELD)
            elif field not in data:
                raise Exception(TransitionError.MISSING_FIELD)

        created_by_team = None
        # First team the user belong to that can make the event.
        if transition.teams_ids_can_transition:
            created_by_team = Team.objects.filter(id__in=transition.teams_ids_can_transition).filter(users=user).first()
        if not created_by_team:
            created_by_team = Team.objects.filter(users=user).first()

        # This will raise if not found, should only happen for invalid workflow.
        node = workflow.get_node_by_key(transition.to_node)

        with transaction.atomic():
            step = BudgetStep.objects.create(
                amount=data.get("amount"),
                created_by=user,
                created_by_team=created_by_team,
                campaign=campaign,
                budget_process=budget_process,
                comment=data.get("comment"),
                transition_key=transition.key,
                node_key_from=budget_process.current_state_key,
                node_key_to=transition.to_node,
            )
            for link_data in data.get("links", []):
                link_serializer = BudgetLinkSerializer(data=link_data)
                link_serializer.is_valid(raise_exception=True)
                link_serializer.save(step=step)

            for file in data.get("files", []):
                step.files.create(file=file, filename=file.name)

            budget_process.current_state_key = transition.to_node
            budget_process.current_state_label = node.label
            budget_process.save()

            send_budget_mails(step, transition, self.context["request"])
            step.is_email_sent = True
            step.save()

            with transaction.atomic():
                field = transition.to_node + "_at_WFEDITABLE"
                if model_field_exists(budget_process, field):
                    # Write the value only if doesn't exist yet, this way we keep track of when a step was first submitted
                    if not getattr(budget_process, field, None):
                        setattr(budget_process, field, step.created_at)
                        setattr(budget_process, "status", transition.to_node)
                        # Custom checks for current workflow. Since we're checking the destination, we'll miss the data for the "concurrent steps".
                        # eg: if we move from state "who_sent_budget" to "gpei_consolidated_budgets", we will miss "unicef_sent_budget" without this check
                        # Needs to be updated when state key names change
                        if transition.to_node == "gpei_consolidated_budgets":
                            if budget_process.who_sent_budget_at_WFEDITABLE is None:
                                setattr(budget_process, "who_sent_budget_at_WFEDITABLE", step.created_at)
                            elif budget_process.unicef_sent_budget_at_WFEDITABLE is None:
                                setattr(budget_process, "unicef_sent_budget_at_WFEDITABLE", step.created_at)
                        if transition.to_node == "approved":
                            if budget_process.approved_by_who_at_WFEDITABLE is None:
                                setattr(budget_process, "approved_by_who_at_WFEDITABLE", step.created_at)
                            elif budget_process.approved_by_unicef_at_WFEDITABLE is None:
                                setattr(budget_process, "approved_by_unicef_at_WFEDITABLE", step.created_at)
                        budget_process.save()

        return step


class TransitionOverrideSerializer(serializers.Serializer):
    new_state_key = serializers.CharField()
    budget_process = serializers.PrimaryKeyRelatedField(queryset=BudgetProcess.objects.all())
    comment = serializers.CharField(required=False)
    files = serializers.ListField(child=serializers.FileField(), required=False)
    links = serializers.JSONField(required=False)
    amount = serializers.FloatField(required=False)

    def save(self, **kwargs):
        data = self.validated_data
        budget_process: BudgetProcess = data["budget_process"]
        campaign: Campaign = budget_process.rounds.first().campaign
        user = self.context["request"].user
        node_keys = data["new_state_key"]
        workflow = get_workflow()

        # Find the override transition in the workflow.
        transition_as_list = list(filter(lambda tr: tr.key == "override", workflow.transitions))

        if len(transition_as_list) == 0:
            raise Exception("override step not found in workflow")

        transition = transition_as_list[0]
        created_by_team = Team.objects.filter(users=user).first()
        # We can get several keys aggregated eg: "submitted_to_rrt,re_submitted_to_rrt", so we split and keep the first one.
        node_key = node_keys.split(",")[0]

        # This will raise if not found, should only happen for invalid workflow.
        to_node = workflow.get_node_by_key(node_key)

        with transaction.atomic():
            step = BudgetStep.objects.create(
                amount=data.get("amount"),
                created_by=user,
                created_by_team=created_by_team,
                campaign=campaign,
                budget_process=budget_process,
                comment=data.get("comment"),
                transition_key="override",
                node_key_from=budget_process.current_state_key,
                node_key_to=to_node.key,
            )
            for link_data in data.get("links", []):
                link_serializer = BudgetLinkSerializer(data=link_data)
                link_serializer.is_valid(raise_exception=True)
                link_serializer.save(step=step)

            for file in data.get("files", []):
                step.files.create(file=file, filename=file.name)

            budget_process.current_state_key = node_key
            budget_process.current_state_label = to_node.label
            budget_process.save()

            send_budget_mails(step, transition, self.context["request"])
            step.is_email_sent = True
            step.save()

            with transaction.atomic():
                field = to_node.key + "_at_WFEDITABLE"
                if model_field_exists(budget_process, field):
                    # Since we override, we don't check that the field is empty.
                    setattr(budget_process, field, step.created_at)
                    setattr(budget_process, "status", to_node.key)
                    order = to_node.order
                    nodes_to_cancel = workflow.get_nodes_after(order)
                    campaign_fields_to_cancel = [node.key + "_at_WFEDITABLE" for node in nodes_to_cancel]
                    # Steps that come after the step we override are cancelled.
                    for field_to_cancel in campaign_fields_to_cancel:
                        if model_field_exists(budget_process, field):
                            if getattr(budget_process, field_to_cancel, None):
                                setattr(budget_process, field_to_cancel, None)
                    budget_process.save()

        return step


class BudgetFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetStepFile
        fields = [
            "id",
            "file",  # url
            "filename",
            "permanent_url",
        ]

    permanent_url = serializers.URLField(source="get_absolute_url", read_only=True)


class BudgetStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetStep
        fields = [
            "id",
            "created_at",
            "created_by_team",
            "created_by",
            "deleted_at",
            "campaign_id",
            "budget_process_id",
            "comment",
            "links",
            "files",
            "amount",
            "transition_key",
            "transition_label",
        ]

    transition_label = serializers.SerializerMethodField()
    files = BudgetFileSerializer(many=True)
    links = BudgetLinkSerializer(many=True)
    created_by_team: serializers.SlugRelatedField = serializers.SlugRelatedField(slug_field="name", read_only=True)
    created_by = UserSerializer()

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_transition_label(self, budget_step: BudgetStep) -> str:
        workflow = get_workflow()
        return workflow.get_transition_label_safe(budget_step.transition_key)


class UpdateBudgetStepSerializer(serializers.ModelSerializer):
    """Update serializer for budget update, the only allowed field is deleted_at to restore it"""

    class Meta:
        model = BudgetStep
        fields = [
            "deleted_at",
        ]


class ExportBudgetProcessSerializer(BudgetProcessSerializer):
    class Meta:
        model = BudgetProcess
        fields = ["obr_name", "current_state_label", "country", "rounds", "updated_at"]
        labels = {
            "obr_name": "OBR name",
            "updated_at": "Last update",
            "country": "Country",
            "rounds": "Rounds",
            "current_state_label": "Budget state",
        }

    country = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    rounds = serializers.SerializerMethodField()

    def get_rounds(self, budget_process: BudgetProcess):
        return ",".join([str(num) for num in budget_process.rounds.values_list("number", flat=True)])

    def get_country(self, budget_process: BudgetProcess):
        return budget_process.country_name

    def get_updated_at(self, budget_process: BudgetProcess):
        return budget_process.updated_at.strftime("%Y-%m-%d")
