from dataclasses import dataclass

import requests


class Workspace:
    def __init__(self, slug, name, description, createdAt, updatedAt, createdBy):
        self.slug = slug
        self.name = name
        self.description = description
        self.created_at = createdAt
        self.updated_at = updatedAt
        self.created_by = createdBy

    def __repr__(self):
        return f"<Workspace slug={self.slug} name={self.name} created={self.created_at}>"

    def to_json(self):
        return {
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by,
        }


class OpenHEXAClient:
    def __init__(self, base_url):
        self.url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json", "User-Agent": "OpenHEXA Python Client"})

    def prepare_object_upload(self, workspace_slug, object_key, content_type):
        raw_upload_url = self.query(
            f"""
            mutation PrepareObjectUpload($input: PrepareObjectUploadInput!) {{
                prepareObjectUpload(input: $input) {{
                    success uploadUrl
                }}
            }}
        """,
            {
                "input": {
                    "workspaceSlug": workspace_slug,
                    "objectKey": object_key,
                    "contentType": content_type,
                }
            },
        )["prepareObjectUpload"]

        return raw_upload_url

    def run_pipeline(self, pipeline_id, config):
        raw_run_pipeline = self.query(
            f"""
            mutation RunPipeline($input: RunPipelineInput!) {{
                runPipeline(input: $input) {{
                    success run {{
                        id
                    }}
                }}
            }}
        """,
            {"input": {"id": pipeline_id, "config": config}},
        )["runPipeline"]

        return raw_run_pipeline

    def upload_object(self, workspace_slug, object_key, file_content, content_type):
        upload_url = self.prepare_object_upload(workspace_slug, object_key, content_type)["uploadUrl"]
        return (requests.put(upload_url, data=file_content, headers={"Content-Type": content_type}),)

    def create_dataset_file_upload_url(self, version_id, content_type, filename):
        raw_upload_url = self.query(
            f"""
            mutation createDatasetVersionFile($input: CreateDatasetVersionFileInput!) {{
                createDatasetVersionFile(input: $input) {{
                    success uploadUrl
                }}
            }}
        """,
            {
                "input": {
                    "versionId": version_id,
                    "contentType": content_type,
                    "uri": filename,
                }
            },
        )["createDatasetVersionFile"]

        return raw_upload_url

    def create_dataset_version(self, datasetId, name, description):
        raw_dataset_version = self.query(
            f"""
            mutation CreateDatasetVersion($input: CreateDatasetVersionInput!) {{
                createDatasetVersion(input: $input) {{
                    success version {{
                        id
                        name
                        description
                        createdAt
                    }}
                }}
            }}
        """,
            {
                "input": {
                    "datasetId": datasetId,
                    "name": name,
                    "description": description,
                }
            },
        )["createDatasetVersion"]["version"]

        return raw_dataset_version

    def create_dataset(self, workspaceSlug, name, description):
        raw_dataset = self.query(
            f"""
            mutation CreateDataset($input: CreateDatasetInput!) {{
                createDataset(input: $input) {{
                    success dataset {{
                        id
                        name
                        description
                        createdAt
                        updatedAt
                    }}
                }}
            }}
        """,
            {
                "input": {
                    "workspaceSlug": workspaceSlug,
                    "name": name,
                    "description": description,
                }
            },
        )["createDataset"]["dataset"]

        return raw_dataset

    def file(self, workspaceSlug, objectKey):
        raw_file = self.query(
            f"""
            mutation GetFile($workspace: String!, $key: String!) {{
                prepareObjectDownload (input: {{ workspaceSlug: $workspace, objectKey: $key }}) {{
                    success downloadUrl
                }}
            }}
        """,
            {"workspace": workspaceSlug, "key": objectKey},
        )["prepareObjectDownload"]

        return raw_file

    def file_contents(self, workspaceSlug, objectKey):
        file = self.file(workspaceSlug, objectKey)

        response = requests.get(file["downloadUrl"])
        return response

    def create_folder(self, workspaceSlug, folderName):
        raw_folder = self.query(
            f"""
            mutation CreateBucketFolderInput($input: CreateBucketFolderInput!) {{
                createBucketFolder(input: $input) {{
                    success 
                    folder {{
                        key
                        name
                        path
                        updatedAt
                    }}
                    errors
                }}
            }}
        """,
            {
                "input": {
                    "workspaceSlug": workspaceSlug,
                    "folderKey": folderName,
                }
            },
        )["createBucketFolder"]["folder"]

        return raw_folder

    def run(self, run_id):
        raw_run = self.query(
            f"""
            query PipelineRun($run: UUID!) {{
                pipelineRun(id: $run) {{
                    id
                    run_id
                    duration
                    progress
                    config
                    status
                    logs
                    executionDate
                    outputs {{
                        ... on BucketObject {{
                            key
                            name
                            path
                        }}
                    }}
                }}
            }}
        """,
            {"run": run_id},
        )["pipelineRun"]

        return raw_run

    def pipelines(self, workspace_slug, start_page=1, page_size=10):
        raw_pipelines = self.query(
            f"""
            query PipelinesForWorkspace($workspace: String!) {{
                pipelines (workspaceSlug: $workspace, page: {start_page}, perPage: {page_size}) {{
                    items {{
                        id
                        name
                        code
                        schedule
                        createdAt
                        updatedAt
                        runs {{ totalItems items {{ id run_id duration progress config status logs executionDate outputs {{ 
                            ... on BucketObject {{ key name path }}
                        }} }} }}
                    }}
                }}
            }}
        """,
            {"workspace": workspace_slug},
        )["pipelines"]

        return raw_pipelines

    def workspace(self, slug):
        raw_workspace = self.query(
            f"""
            query Workspace($slug: String!) {{
                workspace (slug: $slug) {{
                    slug
                    name
                    description
                    createdAt
                    updatedAt
                    createdBy {{ id, email }}
                }}
            }}
        """,
            {"slug": slug},
        )["workspace"]

        return Workspace(**raw_workspace)

    def workspaces(self, start_page=1, page_size=10):
        raw_workspaces = self.query(
            f"""
            query {{
                workspaces (page: {start_page}, perPage: {page_size}) {{
                    items {{
                        slug
                        name
                        description
                        createdAt
                        updatedAt
                        createdBy {{ id, email }}
                    }}
                }}
            }}
        """
        )["workspaces"]["items"]

        workspaces = [Workspace(**ws) for ws in raw_workspaces]

        return workspaces

    def authenticate(
        self,
        with_credentials: None,
        with_token: None,
    ):
        """
        with_credentials: tuple of email and password
        with_token: JWT token
        """
        print("with_credentials", with_credentials)
        if with_credentials:
            resp = self._graphql_request(
                """
                mutation Login($input: LoginInput!) {
                    login(input: $input) {
                        success
                    }
                }
            """,
                {
                    "input": {
                        "email": with_credentials[0],
                        "password": with_credentials[1],
                    }
                },
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            if data["login"]["success"]:
                self.session.headers["Cookie"] = resp.headers["Set-Cookie"]
            else:
                raise Exception("Login failed")
        elif with_token:
            self.session.headers.update({"Authorization": f"Bearer {with_token}"})
        try:
            self.query("""query{me {user {id}}}""")
            return True
        except:
            raise Exception("Authentication failed")

    def _graphql_request(self, operation, variables=None):
        return self.session.post(f"{self.url}/graphql", json={"query": operation, "variables": variables})

    def query(self, operation, variables=None):
        resp = self._graphql_request(operation, variables)
        if resp.status_code == 400:
            raise Exception(resp.json()["errors"][0]["message"])
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("errors"):
            raise Exception(payload["errors"])
        return payload["data"]
