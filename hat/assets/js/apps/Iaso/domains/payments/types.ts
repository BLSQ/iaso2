/* eslint-disable camelcase */
import { Pagination, UrlParams } from 'bluesquare-components';

export type PotentialPaymentParams = UrlParams & {
    change_requests__created_at_after?: string;
    change_requests__created_at_before?: string;
    parent_id?: string;
    forms?: string;
    users?: string;
    user_roles?: string;
};

type PaymenStatus = 'pending' | 'sent' | 'rejected';

type User = {
    id: number;
    username: string;
    first_name: string;
    last_name: string;
};

type OrgUnitChangeRequest = {
    id: number;
    uuid: string;
    org_unit_id: number;
};

export type Payment = {
    id: number;
    status: PaymenStatus;
    created_at: string;
    updated_at: string;
    created_by: User;
    updated_by: User;
    user: User;
    change_requests: OrgUnitChangeRequest[];
};

export type PotentialPayment = {
    id: number;
    status: string;
    user: User;
    change_requests: OrgUnitChangeRequest[];
};
export interface PotentialPaymentPaginated extends Pagination {
    results: PotentialPayment[];
}
