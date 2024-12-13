"""Code to send alert e-mail when there are  incorrect value. this is called in the cron at the moment.

To control who receive the e-mail create edit a polio.Config object with slug emails_for_preparedness_alert
and containing a list of e-mail as json.
e.g. ['test@bluesquarehub.com']
"""

import logging

from django.core.mail import send_mail
from django.template import Engine, Context

from iaso.models.json_config import Config
from plugins.polio.preparedness.summary import get_or_set_preparedness_cache_for_round


def valid_indicator(x):
    if x is None:
        return True
    if isinstance(x, str):
        return x.strip() in ["NA", "N/A"]
    if not isinstance(x, (int, float)):
        return False
    return 0 <= x <= 10


TEMPLATE = """
Hello,

Errors have been found when refreshing the preparedness data for the following upcoming campaigns: 
{% for round_error in rounds %}
{{ round_error.round.campaign.obr_name }} {{ round_error.round.number }} starting on {{ round_error.round.started_at }}
=====================================
Google Spreadsheet Url: {{round_error.round.preparedness_spreadsheet_url}}

{% for error in round_error.errors%}{{ forloop.counter }}. {{error|safe}}
{% endfor %}
{% endfor %}

Sincerely,
The {{ site_name }} Team.
"""


def error_for_rounds(pr):
    errors = []
    for indicator in pr["indicators"].values():
        levels = ["regions", "districts", "national"]
        for level in levels:
            value = indicator[level]
            if not valid_indicator(value):
                error = f"`{indicator['title'].strip()}` invalid at {level} level: {value}"
                errors.append(error)
    return errors


def send_warning_email(round_qs):
    round_errors = []
    for round in round_qs:
        if round.preparedness_sync_status == "FAILURE":
            errors = [
                f"Could not synchronise with the spreadsheet configured. Please check in the Campaign configuration on the platform"
            ]
        else:
            pr = get_or_set_preparedness_cache_for_round(round.campaign, round)
            if not pr or pr.get("status") == "not_sync":
                errors = [f"not synchronised"]
            else:
                try:
                    errors = error_for_rounds(pr)
                except Exception as e:
                    logging.exception(e)
                    errors = ["Unknown error please contact an admin."]
        if errors:
            round_errors.append({"round": round, "errors": errors})

    # send e-mail code
    context = Context({"rounds": round_errors})
    txt_content = Engine.get_default().from_string(TEMPLATE.strip())
    txt_content = txt_content.render(context)
    config, _ = Config.objects.get_or_create(slug="emails_for_preparedness_alert", defaults={"content": []})
    if not config or not config.content:
        logging.warning("no email configured for emails_for_preparedness_alert:")
        print(txt_content)

    emails = config.content
    if round_errors:
        send_mail(
            "Error(s) in preparedness imports",
            message=txt_content,
            from_email=None,
            recipient_list=emails,
        )
        return round_errors
