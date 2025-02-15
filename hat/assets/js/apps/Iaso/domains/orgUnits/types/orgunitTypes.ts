import { Pagination, UrlParams } from 'bluesquare-components';
import { Form } from '../../forms/types/forms';
import { OrgUnit } from './orgUnit';

type FeatureFlag = {
    id: number;
    name: string;
    code: string;
    description: string;
    created_at: number;
    updated_at: number;
};

export type Project = {
    id: number;
    name: string;
    app_id: string | null;
    needs_authentication: boolean;
    created_at: number;
    updated_at: number;
    feature_flags: FeatureFlag[];
};

export type OrgunitType = {
    id: number;
    name: string;
    short_name: string | null;
    depth: number | null;
    created_at: number;
    updated_at: number;
    units_count: number;
    sub_unit_types: OrgunitType[];
    allow_creating_sub_unit_types: OrgunitType[];
    reference_forms: Form[];
    projects: Project[];
    color?: string;
    orgUnits?: OrgUnit[];
};

export type OrgunitTypes = OrgunitType[];

export type OrgunitTypesApi = {
    orgUnitTypes: OrgunitTypes;
};

export interface PaginatedOrgUnitTypes extends Pagination {
    orgUnitTypes: OrgunitType[];
}

export type OrgUnitTypesParams = UrlParams & {
    accountId?: string;
    search?: string;
    with_units_count?: boolean;
};
