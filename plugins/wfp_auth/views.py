import typing
from logging import getLogger

import requests
from allauth.account.utils import perform_login
from allauth.socialaccount import app_settings
from allauth.socialaccount.helpers import render_authentication_error
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.auth0.views import Auth0OAuth2Adapter
from allauth.socialaccount.providers.base import AuthError, ProviderException
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2LoginView,
    OAuth2View,
)
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMultiAlternatives
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.template import loader
from django.views.decorators.csrf import csrf_exempt
from oauthlib.oauth2 import OAuth2Error
from requests import RequestException, HTTPError
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken  # type: ignore

from iaso.api.query_params import APP_ID
from iaso.models import Account, Profile, Project
from .provider import WFPProvider

logger = getLogger(__name__)


class ExtraData(typing.TypedDict):
    email: str
    sub: str  # same as email
    given_name: typing.Optional[str]
    family_name: typing.Optional[str]


def send_mail(subject_template_name, email_template_name, context, from_email, to_email, html_email_template_name=None):
    """
    Send a django.core.mail.EmailMultiAlternatives to `to_email`.
    taken from django.contrib.auth.forms.PasswordResetForm
    """
    subject = loader.render_to_string(subject_template_name, context)
    # Email subject *must not* contain newlines
    subject = "".join(subject.splitlines())
    body = loader.render_to_string(email_template_name, context)

    email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
    if html_email_template_name is not None:
        html_email = loader.render_to_string(html_email_template_name, context)
        email_message.attach_alternative(html_email, "text/html")

    email_message.send()


class WFP2Adapter(Auth0OAuth2Adapter):
    provider_id = WFPProvider.id
    supports_state = True

    settings = app_settings.PROVIDERS.get(provider_id, {})
    provider_base_url = settings.get("AUTH0_URL")

    access_token_url = "{}/token".format(provider_base_url)
    authorize_url = "{}/authorize".format(provider_base_url)
    profile_url = "{}/userinfo".format(provider_base_url)

    def send_new_account_email(self, request: HttpRequest, user):
        to_email = self.settings.get("EMAIL_RECIPIENTS_NEW_ACCOUNT")
        if not to_email:
            logger.warning("no 'EMAIL_RECIPIENTS_NEW_ACCOUNT' configured not sending mail to warn of new account")
            return

        current_site = get_current_site(request=request)
        site_name = current_site.name
        domain = current_site.domain
        profile_url = request.build_absolute_uri(
            f"/dashboard/settings/users/management/accountId/1/search/{user.username}/order/user__username/pageSize/20/page/1"
        )
        context = {
            "new_user": user,
            "profile_url": profile_url,
            "domain": domain,
            "site_name": site_name,
            "user": user,
            # "protocol": "https" if use_https else "http",
        }
        for email in to_email:
            email = email.strip()
            send_mail(
                subject_template_name="wfp_auth/new_account_subject.txt",
                email_template_name="wfp_auth/new_account_email.html",
                from_email=None,
                to_email=email,
                context=context,
            )

    def complete_login(self, request, app, token: str, response) -> SocialAccount:
        # simplify the logic from django-allauth a lot so the flow is less flexible but more followable
        # search if we have a SocialAccount linked to this user
        # if not create one and connect it to an existing user if there is already one with this email
        # contrary to the all auth version it return a SocialAccount
        # Call the userinfo url with the identifying token to get more data on the user
        extra_data_get = requests.get(self.profile_url, params={"access_token": token})
        extra_data_get.raise_for_status()
        extra_data: ExtraData = extra_data_get.json()
        try:
            email = extra_data["email"].lower().strip()
        except KeyError:
            email = extra_data["sub"].lower().strip()
        # the sub is the email, wfp verify it so let's trust this
        uid = extra_data["sub"].lower().strip()
        # We cannot use `AppIdSerializer` because we are in a method **before** `dispatch` and therefore
        # `self.request.query_params` is not set yet. Using `request.query_params` results in:
        # `'WSGIRequest' object has no attribute 'query_params'`
        app_id = request.GET.get(APP_ID, None)

        if app_id:
            account = get_object_or_404(Project, app_id=app_id).account
            if app_id != self.settings["IASO_ACCOUNT_NAME"]:
                uid = f"{app_id}_{uid}"
        else:
            account = Account.objects.get(name=self.settings["IASO_ACCOUNT_NAME"])

        try:
            # user is required, can't use get_or_create
            socialaccount = SocialAccount.objects.get(uid=uid, provider=self.provider_id)
            # update extra data
            socialaccount.extra_data = extra_data
        except SocialAccount.DoesNotExist:
            users = User.objects.filter(iaso_profile__account=account).filter(email=email)
            user = users.first()
            if not user:
                user = User.objects.create(
                    email=email,
                    username=email,
                    first_name=extra_data.get("given_name"),
                    last_name=extra_data.get("family_name"),
                )
                user.set_unusable_password()
                iaso_profile = Profile.objects.create(
                    account=account,
                    user=user,
                )
                user.iaso_profile = iaso_profile
                user.save()
                self.send_new_account_email(request, user)

            socialaccount = SocialAccount(uid=uid, provider=self.provider_id, extra_data=extra_data, user=user)

        socialaccount.save()
        return socialaccount


class WFPCallbackView(OAuth2View):
    adapter: WFP2Adapter

    def dispatch(self, request, *args, **kwargs):
        if "error" in request.GET or "code" not in request.GET:
            # Distinguish cancel from error
            auth_error = request.GET.get("error", None)
            if auth_error == self.adapter.login_cancelled_error:
                error = AuthError.CANCELLED
            else:
                error = AuthError.UNKNOWN
            return render_authentication_error(request, self.adapter.provider_id, error=error)
        app = self.adapter.get_provider().get_app(request)
        client = self.get_client(request, app)

        try:
            access_token = self.adapter.get_access_token_data(request, app, client)
            token = self.adapter.parse_token(access_token)
            token.app = app
            social_account = self.adapter.complete_login(request, app, token=token.token, response=access_token)
            return perform_login(
                request,
                social_account.user,
                email_verification=False,
                redirect_url=request.GET.get("next", "/"),
            )
        except (
            PermissionDenied,
            OAuth2Error,
            RequestException,
            ProviderException,
        ) as e:
            return render_authentication_error(request, self.adapter.provider_id, exception=e)


oauth2_login = OAuth2LoginView.adapter_view(WFP2Adapter)
oauth2_callback = WFPCallbackView.adapter_view(WFP2Adapter)


@csrf_exempt
@api_view(http_method_names=["POST", "GET"])
@authentication_classes([])
@permission_classes([])
def token_view(request):
    """Login workflow via the Mobile Application

    1. User clicks on Login via WFP button in app
    2. Browser opens, user authenticates
    3. App is called as callback, receives token
    4. App calls this view with WFP token
    5. We call the /userinfo/ endpoint on WFP auth server using this token to retrieve user info (email, full name)
    6. We do reconciliation, user creation, sending of email, etc...
    7. Iaso token representing the user connection is created and returned (using DRF simple-jwt like in regular workflow)
    """
    token = request.data.get("token")
    if not token:
        return JsonResponse(
            {
                "result": "error",
                "message": "missing token",
            },
            status=400,
        )
    adapter = WFP2Adapter(request)
    try:
        social_account = adapter.complete_login(request, app=None, token=token, response=None)

    except HTTPError as e:
        logger.exception(str(e))
        if e.response.status_code == 401 and e.response.json()["error"] == "invalid_token":
            return JsonResponse(
                {"message": "Access token validation failed", "result": "error", "error": "invalid_token"}, status=401
            )
        return JsonResponse(
            {"result": "error", "message": "error login to auth server", "details": e.response.text}, status=500
        )
    except Exception as e:
        logger.exception(str(e))
        return JsonResponse({"result": "error", "message": "error login account"})
    user = social_account.user

    # from https://django-rest-framework-simplejwt.readthedocs.io/en/latest/creating_tokens_manually.html
    refresh = RefreshToken.for_user(user)
    return JsonResponse(
        {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        },
        status=200,
    )
