import requests
from django.shortcuts import get_object_or_404

SP_AUTH_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/token"
POWERBI_RESOURCE = "https://analysis.windows.net/powerbi/api"
GRANT_TYPE = "client_credentials"


def get_powerbi_service_principal_token(tenant_id, client_id, secret_value):
    body = {
        "grant_type": GRANT_TYPE,
        "resource": POWERBI_RESOURCE,
        "client_id": client_id,
        "client_secret": secret_value,
    }
    r = requests.post(url=SP_AUTH_URL.format(tenant_id=tenant_id), data=body)
    r.raise_for_status()
    access_token = r.json()["access_token"]
    return access_token


def get_powerbi_report_token_with_sp(sp_access_token, group_id, report_id):
    body = {"accessLevel": "View"}
    url = "https://api.powerbi.com/v1.0/myorg/groups/{}/reports/{}/GenerateToken".format(group_id, report_id)
    headers = {"Content-Type": "application/json", "Authorization": "Bearer %s" % sp_access_token}
    r = requests.post(url=url, json=body, headers=headers)
    r.raise_for_status()
    report_token = r.json()["token"]
    return report_token


def get_powerbi_report_token(group_id, report_id):
    # FIXME : import is not extra but will do till we move this model
    from iaso.models.json_config import Config

    conf = get_object_or_404(Config, slug="powerbi_sp")
    config = conf.content

    sp_access_token = get_powerbi_service_principal_token(
        config["tenant_id"], config["client_id"], config["secret_value"]
    )
    return get_powerbi_report_token_with_sp(sp_access_token, group_id, report_id)


def launch_dataset_refresh(group_id, data_set_id):
    # FIXME : import is not extra but will do till we move this model
    from iaso.models.json_config import Config

    conf = get_object_or_404(Config, slug="powerbi_sp")
    config = conf.content

    sp_access_token = get_powerbi_service_principal_token(
        config["tenant_id"], config["client_id"], config["secret_value"]
    )
    body = {"accessLevel": "View"}
    url = "https://api.powerbi.com/v1.0/myorg/groups/{}/datasets/{}/refreshes".format(group_id, data_set_id)
    headers = {"Content-Type": "application/json", "Authorization": "Bearer %s" % sp_access_token}

    r = requests.post(url=url, json=body, headers=headers)
    r.raise_for_status()
