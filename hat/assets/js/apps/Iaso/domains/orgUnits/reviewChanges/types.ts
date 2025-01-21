import { Pagination, UrlParams } from 'bluesquare-components';
import { User } from '../../../utils/usersUtils';
import { OrgUnitStatus, ShortOrgUnit } from '../types/orgUnit';
import { OrgunitType } from '../types/orgunitTypes';

export type ChangeRequestValidationStatus = 'new' | 'rejected' | 'approved';
export type ApproveOrgUnitParams = UrlParams & {
    parent_id?: string;
    groups?: string;
    org_unit_type_id?: string;
    status?: ChangeRequestValidationStatus;
    created_at_after?: string;
    created_at_before?: string;
    forms?: string;
    userIds?: string;
    userRoles?: string;
    withLocation?: string;
    projectIds?: string;
    paymentStatus?: 'pending' | 'sent' | 'rejected' | 'paid';
    paymentIds?: string; // comma separated ids
    potentialPaymentIds?: string; // comma separated ids
    source_version_id?: string;
    data_source_synchronization_id?: string;
};

export type OrgUnitChangeRequestDetailParams = UrlParams & {
    changeRequestId: string;
};

export type Group = {
    id: number;
    name: string;
};

export type Project = {
    id: number;
    name: string;
};

export type NestedUser = Partial<User>;
export type NestedOrgUnitType = Partial<OrgunitType>;
export type NestedGroup = {
    id: number;
    name: string;
};
export type ExtendedNestedGroup = NestedGroup & {
    left: boolean;
    right: boolean;
};

export type NestedLocation = {
    latitude: number;
    longitude: number;
    altitude: number;
};

export type OrgUnitChangeRequest = {
    id: number;
    uuid: string;
    org_unit_id: number;
    org_unit_uuid: string;
    org_unit_name: string;
    org_unit_type_id: number;
    org_unit_type_name: string;
    org_unit_validation_status: OrgUnitStatus;
    status: ChangeRequestValidationStatus;
    groups: Group[];
    projects: Project[];
    requested_fields: string;
    approved_fields: string[];
    rejection_comment?: string;
    created_by: NestedUser;
    created_at: number;
    updated_by: NestedUser;
    updated_at: number;
    org_unit_parent_id?: number;
    org_unit_parent_name?: string;
};
export type OrgUnitChangeRequests = Array<OrgUnitChangeRequest>;

export interface OrgUnitChangeRequestsPaginated extends Pagination {
    results: OrgUnitChangeRequest[];
}

export type OrgUnitChangeRequestDetails = {
    id: number;
    uuid: string;
    status: ChangeRequestValidationStatus;
    created_by: NestedUser;
    created_at: number;
    updated_by: NestedUser;
    updated_at: number;
    requested_fields: string[];
    approved_fields: string[];
    rejection_comment?: string;
    org_unit: OrgUnitForChangeRequest;
    new_closed_date?: string;
    new_groups: NestedGroup[];
    new_location?: NestedLocation;
    new_location_accuracy?: number;
    new_name?: string;
    new_opening_date?: string;
    new_org_unit_type: NestedOrgUnitType;
    new_parent?: ShortOrgUnit;
    new_reference_instances: InstanceForChangeRequest[];
    old_closed_date?: string;
    old_groups: NestedGroup[];
    old_location?: NestedLocation;
    old_location_accuracy?: number;
    old_name?: string;
    old_opening_date?: string;
    old_org_unit_type: NestedOrgUnitType;
    old_parent?: ShortOrgUnit;
    old_reference_instances: InstanceForChangeRequest[];
};

type OrgUnitForChangeRequest = {
    id: number;
    parent?: ShortOrgUnit;
    name: string;
    org_unit_type: NestedOrgUnitType;
    groups: NestedGroup[];
    location?: NestedLocation;
    opening_date?: string;
    closed_date?: string;
    reference_instances: InstanceForChangeRequest[];
    validation_status: OrgUnitStatus;
};

export type InstanceForChangeRequest = {
    id: number;
    form_id: string;
    form_name: string;
    values: any;
};
