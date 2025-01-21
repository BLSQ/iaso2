import { UseQueryResult } from 'react-query';
import { makeUrlWithParams } from '../../../../../libs/utils';
import { getRequest } from '../../../../../libs/Api';
import { useSnackQuery } from '../../../../../libs/apiHooks';
import {
    OrgUnitChangeRequestsPaginated,
    ApproveOrgUnitParams,
} from '../../types';
import { apiUrl } from '../../constants';
import { useLocale } from '../../../../app/contexts/LocaleContext';

const getOrgUnitChangeProposals = (url: string) => {
    return getRequest(url) as Promise<OrgUnitChangeRequestsPaginated>;
};

export const useGetApprovalProposals = (
    params: ApproveOrgUnitParams,
): UseQueryResult<OrgUnitChangeRequestsPaginated, Error> => {
    const { locale } = useLocale();
    const apiParams = {
        parent_id: params.parent_id,
        groups: params.groups,
        org_unit_type_id: params.org_unit_type_id,
        status: params.status,
        order: params.order || '-updated_at',
        limit: params.pageSize || 10,
        page: params.page,
        created_at_after: params.created_at_after,
        created_at_before: params.created_at_before,
        forms: params.forms,
        users: params.userIds,
        user_roles: params.userRoles,
        with_location: params.withLocation,
        projects: params.projectIds,
        payment_status: params.paymentStatus,
        payment_ids: params.paymentIds,
        source_version_id: params.source_version_id,
        potential_payment_ids: params.potentialPaymentIds,
        data_source_synchronization_id: params.data_source_synchronization_id,
    };

    const url = makeUrlWithParams(apiUrl, apiParams);
    return useSnackQuery({
        // Including locale in the query key because we need to make a call to update translations coming from the backend
        queryKey: ['getApprovalProposals', url, locale],
        queryFn: () => getOrgUnitChangeProposals(url),
        options: {
            staleTime: 1000 * 60 * 15, // in MS
            cacheTime: 1000 * 60 * 5,
            keepPreviousData: true,
            retryOnMount: false, // If not set to false, the query will retry on mount which will cause an endless loop
            retry: false, // Will not retry failing query. Has to be used with retryOnMount, to prevent endless loop
        },
    });
};
