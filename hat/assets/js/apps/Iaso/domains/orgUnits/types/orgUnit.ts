import { Pagination, UrlParams } from 'bluesquare-components';
import { ReactNode } from 'react';
import { GeoJson } from '../../../components/maps/types';
import { Nullable } from '../../../types/utils';
import { File, Instance } from '../../instances/types/instance';
import { OrgunitType } from './orgunitTypes';
import { Shape } from './shapes';

export type ShortOrgUnit = {
    name: string;
    id: number;
    geo_json?: GeoJson;
};
export type Group = {
    created_at: number;
    updated_at: number;
    id: number;
    name: string;
    source_ref: Nullable<string>;
    source_version: number;
};

export type OrgunitInititialState = {
    id: number;
    name: string;
    org_unit_type_id?: string;
    groups: Array<(unknown & { id: number }) | number>;
    sub_source?: string;
    validation_status?: string;
    aliases: string[];
    source_id?: number;
    parent?: ParentOrgUnit;
    source_ref?: string;
    reference_instance_id?: Nullable<number>;
    opening_date?: Date;
    closed_date?: Date;
};

export type OrgUnitStatus = 'VALID' | 'NEW' | 'REJECTED';

export type ParentOrgUnit = {
    name: string;
    id: number;
    org_unit_type_name: string;
    org_unit_type_id: number;
    parent: ParentOrgUnit;
    parent_name?: string;
    source?: string;
    source_id?: number;
    validation_status?: OrgUnitStatus;
};

export type OrgUnit = {
    name: string;
    short_name: string;
    id: number;
    sub_source: string;
    sub_source_id: string | undefined;
    source_ref: string;
    source_url: null;
    parent_id: number;
    validation_status: OrgUnitStatus;
    parent_name: string;
    parent: ParentOrgUnit;
    org_unit_type_id: number;
    creator: Record<string, any>;
    created_at: number;
    updated_at: number;
    aliases?: string[];
    latitude?: number;
    longitude?: number;
    altitude?: number;
    geo_json?: Shape | undefined;
    has_geo_json: boolean;
    org_unit_type_name: string;
    org_unit_type_depth: Nullable<number>;
    source: string;
    source_id: number;
    version: number;
    groups: Group[];
    org_unit_type: OrgunitType;
    org_unit_type_short_name?: string;
    search_index?: number;
    reference_instance_id: Nullable<number>;
    reference_instances: Instance[];
    catchment?: Shape;
    reference_instance_action?: string;
    opening_date?: Date;
    closed_date?: Date;
    default_image?: File;
};
export interface PaginatedOrgUnits extends Pagination {
    orgunits: OrgUnit[];
}

export type OrgUnitParams = UrlParams & {
    locationLimit: string;
    tab?: string;
    searchTabIndex: string;
    searchActive?: string;
    searches: string;
};

export type OrgUnitsApi = {
    orgunits: OrgUnit[];
};
type FormState<T> = {
    value?: T;
    errors?: string[];
};
type FormStateRequired<T> = {
    value: T;
    errors?: string[];
};

export type OrgUnitState = {
    id: FormStateRequired<number>;
    name: FormStateRequired<string>;
    org_unit_type_id: FormStateRequired<string>;
    groups: FormState<number[]>;
    sub_source: FormState<string>;
    validation_status: FormState<string>;
    aliases: FormState<string>;
    source_id: FormState<number>;
    source: FormState<string>;
    parent: FormState<OrgUnit>;
    source_ref: FormState<string>;
    creator: FormStateRequired<Record<string, any>>;
    reference_instance_id: FormState<number>;
    opening_date: FormState<number>;
    closed_date: FormState<number>;
};

export type Action = {
    id: string;
    icon: ReactNode;
    disabled?: boolean;
};

export type ActionsType = Action[];
