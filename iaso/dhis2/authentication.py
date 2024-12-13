import requests
from django.contrib.auth import login
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from requests.auth import HTTPBasicAuth

from iaso.models import Profile, ExternalCredentials


def dhis2_callback(request, dhis2_slug):
    if request.GET.get("code"):
        ext_credentials = get_object_or_404(ExternalCredentials, name=dhis2_slug)

        DHIS2_SERVER_URL = ext_credentials.login
        REDIRECT_URI = ext_credentials.url
        IASO_DHIS2_SECRET = ext_credentials.password

        code = request.GET.get("code", None)

        payload = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI + "api/dhis2/{}/login/".format(dhis2_slug),
            "client_id": dhis2_slug,
        }

        response = requests.post(
            DHIS2_SERVER_URL + "uaa/oauth/token",
            auth=HTTPBasicAuth(dhis2_slug, IASO_DHIS2_SECRET),
            headers={"Content-Type": "Accept: application/json"},
            params=payload,
        )

        response.raise_for_status()

        if response.json()["access_token"]:
            access_token = response.json()["access_token"]

            user_info = requests.get(
                DHIS2_SERVER_URL + "api/me", headers={"Authorization": "Bearer {}".format(access_token)}
            )

            user_dhis2_id = user_info.json()["id"]

            try:
                user = Profile.objects.get(dhis2_id=user_dhis2_id, account=ext_credentials.account).user
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                request.session.set_expiry(3600 * 24)
                return HttpResponseRedirect(redirect_to="/")
            except ObjectDoesNotExist:
                return HttpResponse(
                    "Iaso User with DHIS2 credentials < {} > does not exists.".format(
                        user_info.json()["userCredentials"]["name"]
                    )
                )
        else:
            return HttpResponse("Error: {}".format(response.json()))

    return HttpResponse("ok")
