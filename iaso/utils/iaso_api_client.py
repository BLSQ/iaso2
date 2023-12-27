import requests
import time


class IasoClient:
    def __init__(self, server_url):
        self.debug = False
        self.server_url = server_url
        self.headers = {}

    def authenticate_with_username_and_password(self, username, password):
        credentials = {"username": username, "password": password}
        r = requests.post(self.server_url + "/api/token/", json=credentials)
        token = r.json().get("access")
        self.authenticate_with_token(token)

    def authenticate_with_token(self, token):
        self.headers["Authorization"] = "Bearer %s" % token

    def post(self, url, json=None, data=None, files=None):
        self.log(url, json)
        r = requests.post(self.server_url + url, json=json, data=data, headers=self.headers, files=files)
        resp = None
        try:
            resp = r.json()
            r.raise_for_status()
        except Exception as e:
            print(resp, r)
            raise e
        self.log(resp)
        return resp

    def patch(self, url, json=None, data=None, files=None):
        self.log(url, json)
        print(url, json)
        r = requests.patch(self.server_url + url, json=json, data=data, headers=self.headers, files=files)
        resp = None
        try:
            resp = r.json()
            r.raise_for_status()
        except Exception as e:
            print(resp, r)
            raise e
        self.log(resp)
        return resp

    def put(self, url, json=None, data=None, files=None):
        self.log(url, json)
        print(url, json)
        r = requests.put(self.server_url + url, json=json, data=data, headers=self.headers, files=files)
        resp = None
        try:
            resp = r.json()
            r.raise_for_status()
        except Exception as e:
            print(resp, r)
            raise e
        self.log(resp)
        return resp

    def get(self, url, params=None, parseResult=True):
        r = requests.get(self.server_url + url, params=params, headers=self.headers)
        resp = r
        try:
            if parseResult:
                resp = r.json()
            r.raise_for_status()
        except Exception as e:
            print(resp, r)
            raise e
        self.log(url, resp)
        return resp

    def wait_task_completion(self, task_to_wait):
        print(f"\tWaiting for async task '{task_to_wait['task']['name']}'")
        count = 0
        imported = False
        while not imported and count < 120:
            task = self.get(f"/api/tasks/{task_to_wait['task']['id']}")
            imported = task["status"] == "SUCCESS"

            if task["status"] == "ERRORED":
                raise Exception(f"Task failed {task}")
            time.sleep(2)
            count += 5
            print("\t\tWaiting:", count, "s elapsed", task.get("progress_message"))

    def log(self, arg1, arg2=None):
        if self.debug:
            print(arg1, arg2)
