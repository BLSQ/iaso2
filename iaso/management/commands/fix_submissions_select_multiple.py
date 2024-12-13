from django.core.management.base import BaseCommand
from datetime import datetime
import iaso.models as m

# This is one time command to "reparse" the xml to json
# All submissions for forms with select_multiple has to be reparse
# the select_multiple questions have been ignored since the merge/deploy of https://github.com/BLSQ/iaso/pull/1265
#
# testing on a small subset on your dev env
#
#    docker compose run --rm iaso manage seed_test_data --mode=seed --dhis2version=2.40.4.1
#    docker compose run --rm iaso manage fix_submissions_select_multiple


class Command(BaseCommand):
    def handle(self, *args, **options):
        date_limite = datetime(2024, 6, 1)

        for form in m.Form.objects.all():
            form_has_select_multiple = False
            for version in form.form_versions.all():
                questions = [q for q in version.questions_by_name().values()]
                has_select_multiple = [q for q in questions if "type" in q and q["type"] == "select all that apply"]
                if len(has_select_multiple) > 0:
                    form_has_select_multiple = True

            if form_has_select_multiple:
                query_set = form.instances.filter(created_at__gte=date_limite)
                count = query_set.count()
                print("****", form.name, count)
                if count > 0:
                    print("form", form.name, form.form_id, "instances count", count, "since", date_limite)

                    for instance in query_set.all().iterator(chunk_size=2000):
                        instance.json = None
                        instance.get_and_save_json_of_xml()
