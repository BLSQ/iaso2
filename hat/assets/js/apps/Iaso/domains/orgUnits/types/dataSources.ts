export type Version = {
    number: number;
    description?: string;
    id: number;
    created_at: number;
    updated_at: number;
    org_units_count: number;
    is_default?: boolean;
    data_source?: number;
    data_source_name?: string;
};

export type Project = {
    id: number;
    name: string;
    app_id: string;
};

type Credentials = {
    id: number;
    name: string;
    login: string;
    url: string;
    isValid: boolean;
};

export type DataSource = {
    id: number;
    name: string;
    read_only: string | null;
    description: string;
    created_at: string;
    updated_at: string;
    versions: Version[];
    url: string;
    projects: Project[];
    default_version?: Version;
    credentials?: Credentials;
    color?: string;
};

export type DataSources = DataSource[];

export type DataSourcesApi = {
    sources: DataSources;
};
