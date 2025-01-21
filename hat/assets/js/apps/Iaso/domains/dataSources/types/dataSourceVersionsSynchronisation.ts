export type NestedUser = {
    id: number;
    username: string;
    first_name: string;
    last_name: string;
    full_name: string;
};

export type NestedAccount = {
    id: number;
    name: string;
    default_version: number;
};

export type NestedSourceVersion = {
    id: number;
    number: number;
    description: string;
    data_source: number;
    data_source_name: string;
};

export type DataSourceVersionsSynchronisation = {
    id: number;
    name?: string;
    source_version_to_update?: NestedSourceVersion;
    source_version_to_compare_with?: NestedSourceVersion;
    count_create?: number;
    count_update?: number;
    account?: NestedAccount;
    user?: NestedUser;
    created_at?: string; // DateTime.
    updated_at?: string; // DateTime.
};

export type DataSourceVersionsSynchronisationDropdown = {
    value: string;
    label: string;
};
