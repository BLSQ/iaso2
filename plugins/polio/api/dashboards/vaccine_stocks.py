import csv
import datetime as dt
import functools
from collections import defaultdict
from datetime import datetime, timedelta
from logging import getLogger
from typing import Optional

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Max, Min
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from requests import HTTPError
from rest_framework import viewsets

from iaso.api.common import CONTENT_TYPE_CSV
from iaso.models import OrgUnit
from plugins.polio.api.common import (
    convert_dicts_to_table,
    find_campaign_on_day,
    find_orgunit_in_cache,
    get_url_content,
)
from plugins.polio.api.common import make_orgunits_cache
from plugins.polio.models import Campaign
from iaso.models.json_config import Config
from plugins.polio.vaccines_email import send_vaccines_notification_email

logger = getLogger(__name__)


def handle_ona_request_with_key(request, key, country_id=None):
    as_csv = request.GET.get("format", None) == "csv"
    config = get_object_or_404(Config, slug=key)
    res = []
    failure_count = 0
    campaigns = Campaign.objects.all().filter(deleted_at=None)

    form_count = 0
    find_campaign_on_day_cached = functools.lru_cache(None)(find_campaign_on_day)
    stats = {
        "7days": {"ok": defaultdict(int), "failure": defaultdict(int)},
        "alltime": {"ok": defaultdict(int), "failure": defaultdict(int)},
    }
    for config in config.content:
        cid = int(country_id) if (country_id and country_id.isdigit()) else None
        if country_id is not None and config.get("country_id", None) != cid:
            continue

        country = OrgUnit.objects.get(id=config["country_id"])

        facilities = (
            OrgUnit.objects.hierarchy(country)
            .filter(org_unit_type_id__category="HF")
            .only("name", "id", "parent", "aliases")
            .prefetch_related("parent")
        )
        cache = make_orgunits_cache(facilities)
        logger.info(f"vaccines country cache len {len(cache)}")
        # Add fields to speed up detection of campaign day
        campaign_qs = campaigns.filter(country_id=country.id).annotate(
            last_start_date=Max("rounds__started_at"),
            start_date=Min("rounds__started_at"),
            end_date=Max("rounds__ended_at"),
        )

        # If all the country's campaigns has been over for more than five day, don't fetch submission from remote server
        # use cache
        last_campaign_date_agg = campaign_qs.aggregate(last_date=Max("end_date"))
        last_campaign_date: Optional[dt.date] = last_campaign_date_agg["last_date"]
        prefer_cache = last_campaign_date and (last_campaign_date + timedelta(days=5)) < dt.date.today()
        try:
            forms = get_url_content(
                url=config["url"],
                login=config["login"],
                password=config["password"],
                minutes=config.get("minutes", 60),
                prefer_cache=prefer_cache,
            )
        except HTTPError:
            # Send an email in case the WHO server returns an error.
            logger.exception(f"error refreshing ona data for {country.name}, skipping country")
            email_config = Config.objects.filter(slug="vaccines_emails").first()

            if email_config and email_config.content:
                emails = email_config.content
                send_vaccines_notification_email(config["login"], emails)
            continue
        logger.info(f"vaccines  {country.name}  forms: {len(forms)}")

        for form in forms:
            try:
                today_string = form["today"]
                today = datetime.strptime(today_string, "%Y-%m-%d").date()
                response_id = form.get("response_ID", None)
                campaign = find_campaign_on_day_cached(campaign_qs, today, response_id)
                district_name = form.get("District", None)
                if not district_name:
                    district_name = form.get("district", "")
                facility_name = form.get("facility", None)
                # some form version for Senegal had their facility column as Facility with an uppercase.
                if not facility_name:
                    facility_name = form.get("Facility", "")

                if facility_name:
                    facility = find_orgunit_in_cache(cache, facility_name, district_name)
                    form["facility_id"] = facility.id if facility else None
                else:
                    form["facility_id"] = None

                form["country"] = country.name

                if campaign:
                    form["campaign_id"] = campaign.id
                    form["epid"] = campaign.epid
                    form["obr"] = campaign.obr_name
                else:
                    form["campaign_id"] = None
                    form["epid"] = None
                    form["obr"] = None

                res.append(form)
                form_count += 1

                success = form["facility_id"] != None and form["campaign_id"] != None
                stats_key = "ok" if success else "failure"
                stats["alltime"][stats_key][country.name] = stats["alltime"][stats_key][country.name] + 1
                if (datetime.utcnow().date() - today).days <= 7:
                    stats["7days"][stats_key][country.name] = stats["7days"][stats_key][country.name] + 1
            except Exception as e:
                logger.exception(f"failed parsing of {form}", exc_info=e)
                failure_count += 1
    print("parsed:", len(res), "failed:", failure_count)
    res = convert_dicts_to_table(res)

    if len(stats["7days"]["failure"]) > 1:  # let's send an email if there are recent failures
        email_text = "Forms not appearing in %s for the last 7 days \n" % key.upper()
        config = get_object_or_404(Config, slug="refresh_error_mailing_list")
        mails = config.content["mails"].split(",")  # format should be: {"mails": "a@a.b,b@b.a"}
        for country in stats["7days"]["failure"]:
            new_line = "\n%d\t%s" % (stats["7days"]["failure"][country], country)
            email_text += new_line
        email_text += "\n\nForms correctly handled in %s for the last 7 days\n" % key.upper()
        for country in stats["7days"]["ok"]:
            new_line = "\n%d\t%s" % (stats["7days"]["ok"][country], country)
            email_text += new_line
        send_mail(
            "Recent errors for {}".format(key.upper()),
            email_text,
            settings.DEFAULT_FROM_EMAIL,
            mails,
        )
    if as_csv:
        response = HttpResponse(content_type=CONTENT_TYPE_CSV)
        writer = csv.writer(response)
        for item in res:
            writer.writerow(item)
        return response
    else:
        return JsonResponse(res, safe=False)


class VaccineStocksViewSet(viewsets.ViewSet):
    """
    Endpoint used to transform Vaccine Stocks data from existing ODK forms stored in ONA.
    sample config: [{"url": "https://afro.who.int/api/v1/data/yyy", "login": "d", "country": "hyrule", "password": "zeldarules", "country_id": 2115781}]
     A notification email can be automatically send for in case of login error by creating a config into polio under the name vaccines_emails.  The content must be an array of emails.
    """

    @method_decorator(cache_page(60 * 60 * 1))  # cache result for one hour
    def list(self, request):
        return handle_ona_request_with_key(request, "vaccines")

    @method_decorator(cache_page(60 * 60 * 1))  # cache result for one hour
    def retrieve(self, request, pk=None):
        return handle_ona_request_with_key(request, "vaccines", country_id=pk)
