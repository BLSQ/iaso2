/* eslint-disable camelcase */
import { UseMutationResult, UseQueryResult } from 'react-query';
import { UrlParams } from 'bluesquare-components';
import {
    deleteRequest,
    getRequest,
    patchRequest,
    postRequest,
} from '../../../../../../../../hat/assets/js/apps/Iaso/libs/Api';
import { useUrlParams } from '../../../../../../../../hat/assets/js/apps/Iaso/hooks/useUrlParams';
import {
    FormattedApiParams,
    useApiParams,
} from '../../../../../../../../hat/assets/js/apps/Iaso/hooks/useApiParams';
import {
    useSnackMutation,
    useSnackQuery,
} from '../../../../../../../../hat/assets/js/apps/Iaso/libs/apiHooks';
import {
    StockManagementListParams,
    StockManagementDetailsParams,
    StockVariationParams,
} from '../types';

import {
    CAMPAIGNS_ENDPOINT,
    useGetCampaigns,
} from '../../../Campaigns/hooks/api/useGetCampaigns';
import { commaSeparatedIdsToStringArray } from '../../../../../../../../hat/assets/js/apps/Iaso/utils/forms';

const defaults = {
    order: 'country',
    pageSize: 20,
    page: 1,
};
const options = {
    select: data => {
        if (!data) return { results: [] };
        return data;
    },
    keepPreviousData: true,
    staleTime: 1000 * 60 * 15, // in MS
    cacheTime: 1000 * 60 * 5,
    // automatically refetch after a time to update data changed by other users
    refetchInterval: 1000 * 60 * 5,
};

const apiUrl = '/api/polio/vaccine/vaccine_stock/';
const modalUrl = '/api/polio/vaccine/stock/';

// eslint-disable-next-line no-unused-vars, @typescript-eslint/no-unused-vars
const getVaccineStockList = async (params: FormattedApiParams) => {
    const queryString = new URLSearchParams(params).toString();
    return getRequest(`${apiUrl}?${queryString}`);
};

export const useGetVaccineStockList = (
    params: StockManagementListParams,
): UseQueryResult<any, any> => {
    const safeParams = useUrlParams(params, defaults);
    const apiParams = useApiParams(safeParams);
    // TODO all quey keys here need to be invalidated if an update has been made in supplychain > VAR part of the module
    return useSnackQuery({
        queryKey: [
            'vaccine-stock-list',
            apiParams,
            apiParams.page,
            apiParams.limit,
            apiParams.order,
        ],
        queryFn: () => getVaccineStockList(apiParams),
        options,
    });
};

// eslint-disable-next-line no-unused-vars, @typescript-eslint/no-unused-vars
const getUsableVials = async (id: string, queryString: string) => {
    return getRequest(`${apiUrl}${id}/usable_vials/?${queryString}`);
};

// Need to pass id to apiUrl
export const useGetUsableVials = (
    params: StockManagementDetailsParams,
    enabled: boolean,
): UseQueryResult<any, any> => {
    const {
        usableVialsOrder: order,
        usableVialsPage: page,
        usableVialsPageSize: pageSize,
    } = params;
    const safeParams = useUrlParams({
        order,
        page,
        pageSize,
    } as Partial<UrlParams>);
    const apiParams = useApiParams(safeParams);
    const { id } = params;
    const queryString = new URLSearchParams(apiParams).toString();
    return useSnackQuery({
        queryKey: ['usable-vials', queryString, id],
        queryFn: () => getUsableVials(id, queryString),
        options: { ...options, enabled },
    });
};

// eslint-disable-next-line no-unused-vars, @typescript-eslint/no-unused-vars
const getUnusableVials = async (id: string, queryString: string) => {
    return getRequest(`${apiUrl}${id}/get_unusable_vials/?${queryString}`);
};
// Need to pass id to apiUrl
// Splitting both hooks to be able to store both payloads in the cache and avoid refteching with each tab change
export const useGetUnusableVials = (
    params: StockManagementDetailsParams,
    enabled: boolean,
): UseQueryResult<any, any> => {
    const {
        unusableVialsOrder: order,
        unusableVialsPage: page,
        unusableVialsPageSize: pageSize,
    } = params;
    const safeParams = useUrlParams({
        order,
        page,
        pageSize,
    } as Partial<UrlParams>);
    const { id } = params;
    const apiParams = useApiParams(safeParams);
    const queryString = new URLSearchParams(apiParams).toString();
    return useSnackQuery({
        queryKey: ['unusable-vials', queryString, id],
        queryFn: () => getUnusableVials(id, queryString),
        options: { ...options, enabled },
    });
};

// eslint-disable-next-line @typescript-eslint/no-unused-vars, no-unused-vars
const getStockManagementSummary = async (id?: string) => {
    return getRequest(`${apiUrl}${id}/summary/`);
};

export const useGetStockManagementSummary = (
    id?: string,
): UseQueryResult<any, any> => {
    return useSnackQuery({
        queryKey: ['stock-management-summary', id],
        queryFn: () => getStockManagementSummary(id),
        options: { ...options, enabled: Boolean(id) },
    });
};

const getFormAList = async (queryString: string) => {
    return getRequest(`${modalUrl}outgoing_stock_movement/?${queryString}`);
};

export const useGetFormAList = (
    params: StockVariationParams,
    enabled: boolean,
): UseQueryResult<any, any> => {
    const {
        formaOrder: order,
        formaPage: page,
        formaPageSize: pageSize,
        id: vaccine_stock,
    } = params;
    const safeParams = useUrlParams({
        order,
        page,
        pageSize,
        vaccine_stock,
    } as Partial<UrlParams>);
    const apiParams = useApiParams(safeParams);
    const queryString = new URLSearchParams(apiParams).toString();
    return useSnackQuery({
        queryKey: ['formA', queryString, vaccine_stock],
        queryFn: () => getFormAList(queryString),
        options: { ...options, enabled },
    });
};
const getDestructionList = async (queryString: string) => {
    return getRequest(`${modalUrl}destruction_report/?${queryString}`);
};

export const useGetDestructionList = (
    params: StockVariationParams,
    enabled: boolean,
): UseQueryResult<any, any> => {
    const {
        destructionOrder: order,
        destructionPage: page,
        destructionPageSize: pageSize,
        id: vaccine_stock,
    } = params;
    const safeParams = useUrlParams({
        order,
        page,
        pageSize,
        vaccine_stock,
    } as Partial<UrlParams>);
    const apiParams = useApiParams(safeParams);
    const queryString = new URLSearchParams(apiParams).toString();
    return useSnackQuery({
        queryKey: ['destruction', queryString, vaccine_stock],
        queryFn: () => getDestructionList(queryString),
        options: { ...options, enabled },
    });
};
const getIncidentList = async (queryString: string) => {
    return getRequest(`${modalUrl}incident_report/?${queryString}`);
};

export const useGetIncidentList = (
    params: StockVariationParams,
    enabled: boolean,
): UseQueryResult<any, any> => {
    const {
        incidentOrder: order,
        incidentPage: page,
        incidentPageSize: pageSize,
        id: vaccine_stock,
    } = params;
    const safeParams = useUrlParams({
        order,
        page,
        pageSize,
        vaccine_stock,
    } as Partial<UrlParams>);
    const apiParams = useApiParams(safeParams);
    const queryString = new URLSearchParams(apiParams).toString();
    return useSnackQuery({
        queryKey: ['incidents', queryString, vaccine_stock],
        queryFn: () => getIncidentList(queryString),
        options: { ...options, enabled },
    });
};

// TODO get list of campaigns filtered by active vacccine
export const useCampaignOptions = (countryName: string): UseQueryResult => {
    const queryOptions = {
        select: data => {
            if (!data) return [];
            return data
                .filter(c => c.top_level_org_unit_name === countryName)
                .map(c => {
                    return {
                        label: c.obr_name,
                        value: c.obr_name,
                    };
                });
        },
        keepPreviousData: true,
        staleTime: 1000 * 60 * 15, // in MS
        cacheTime: 1000 * 60 * 5,
    };
    return useGetCampaigns({}, CAMPAIGNS_ENDPOINT, undefined, queryOptions);
};

const createEditFormA = async (body: any) => {
    const copy = { ...body };
    const { lot_numbers } = body;
    if (lot_numbers && !Array.isArray(lot_numbers)) {
        const lotNumbersArray = commaSeparatedIdsToStringArray(lot_numbers);
        copy.lot_numbers = lotNumbersArray;
    }
    if (body.id) {
        return patchRequest(
            `${modalUrl}outgoing_stock_movement/${body.id}/`,
            copy,
        );
    }
    return postRequest(`${modalUrl}outgoing_stock_movement/`, copy);
};

export const useSaveFormA = () => {
    return useSnackMutation({
        mutationFn: body => createEditFormA(body),
        invalidateQueryKey: [
            'formA',
            'vaccine-stock-list',
            'usable-vials',
            'stock-management-summary',
            'unusable-vials',
        ],
    });
};
const createEditDestruction = async (body: any) => {
    const copy = { ...body };
    const { lot_numbers } = body;
    if (lot_numbers && !Array.isArray(lot_numbers)) {
        const lotNumbersArray = commaSeparatedIdsToStringArray(lot_numbers);
        copy.lot_numbers = lotNumbersArray;
    }
    if (body.id) {
        return patchRequest(`${modalUrl}destruction_report/${body.id}/`, copy);
    }
    return postRequest(`${modalUrl}destruction_report/`, copy);
};

export const useSaveDestruction = () => {
    return useSnackMutation({
        mutationFn: body => createEditDestruction(body),
        invalidateQueryKey: [
            'destruction',
            'vaccine-stock-list',
            'usable-vials',
            'stock-management-summary',
            'unusable-vials',
        ],
    });
};
const createEditIncident = async (body: any) => {
    const copy = { ...body };
    const { lot_numbers } = body;
    if (lot_numbers && !Array.isArray(lot_numbers)) {
        const lotNumbersArray = commaSeparatedIdsToStringArray(lot_numbers);
        copy.lot_numbers = lotNumbersArray;
    }
    if (body.id) {
        return patchRequest(`${modalUrl}incident_report/${body.id}/`, copy);
    }
    return postRequest(`${modalUrl}incident_report/`, copy);
};

export const useSaveIncident = () => {
    return useSnackMutation({
        mutationFn: body => createEditIncident(body),
        invalidateQueryKey: [
            'incidents',
            'vaccine-stock-list',
            'usable-vials',
            'stock-management-summary',
            'unusable-vials',
        ],
    });
};

const saveVaccineStock = body => {
    return postRequest(apiUrl, body);
};

export const useSaveVaccineStock = () => {
    return useSnackMutation({
        mutationFn: body => saveVaccineStock(body),
        invalidateQueryKey: 'vaccine-stock-list',
    });
};

const deleteVaccineStock = (id: string) => {
    return deleteRequest(`${apiUrl}${id}`);
};

export const useDeleteVaccineStock = (): UseMutationResult => {
    return useSnackMutation({
        mutationFn: deleteVaccineStock,
        invalidateQueryKey: 'vaccine-stock-list',
    });
};
