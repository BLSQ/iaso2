export type User = {
    id: number;
    username: string;
    first_name: string;
    last_name: string;
    full_name: string;
};

export type Account = {
    id: number;
    name: string;
    default_version: number;
};

export type SourceVersion = {
    id: number;
    number: number;
    description: string;
    data_source: number;
    data_source_name: string;
};

export type DataSourceVersionsSynchronisation = {
    id: number;
    name?: string;
    source_version_to_update?: SourceVersion;
    source_version_to_compare_with?: SourceVersion;
    count_create?: number;
    count_update?: number;
    account?: Account;
    user?: User;
    created_at?: string; // DateTime.
    updated_at?: string; // DateTime.
};
