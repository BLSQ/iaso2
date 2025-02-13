import { UrlParams, useSafeIntl } from 'bluesquare-components';
import { useMemo } from 'react';
import { UseMutationResult, UseQueryResult } from 'react-query';
import {
    FormattedApiParams,
    useApiParams,
} from '../../../../../../../../hat/assets/js/apps/Iaso/hooks/useApiParams';
import { useUrlParams } from '../../../../../../../../hat/assets/js/apps/Iaso/hooks/useUrlParams';
import {
    deleteRequest,
    getRequest,
    postRequest,
} from '../../../../../../../../hat/assets/js/apps/Iaso/libs/Api';
import {
    useSnackMutation,
    useSnackQuery,
} from '../../../../../../../../hat/assets/js/apps/Iaso/libs/apiHooks';
import {
    StockManagementDetailsParams,
    StockManagementListParams,
    StockVariationParams,
} from '../types';

import { DropdownOptions } from '../../../../../../../../hat/assets/js/apps/Iaso/types/utils';
import { commaSeparatedIdsToStringArray } from '../../../../../../../../hat/assets/js/apps/Iaso/utils/forms';
import {
    CAMPAIGNS_ENDPOINT,
    useGetCampaigns,
} from '../../../Campaigns/hooks/api/useGetCampaigns';
import { patchRequest2, postRequest2 } from '../../SupplyChain/hooks/api/vrf';
import MESSAGES from '../messages';

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

const getUnusableVials = async (id: string, queryString: string) => {
    return getRequest(`${apiUrl}${id}/get_unusable_vials/?${queryString}`);
};
// Need to pass id to apiUrl
// Splitting hooks to be able to store payloads in the cache and avoid refetching with each tab change
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

const getEarmarked = async (id: string, queryString: string) => {
    return getRequest(`${apiUrl}${id}/get_earmarked_stock/?${queryString}`);
};
// Need to pass id to apiUrl
// Splitting hooks to be able to store both payloads in the cache and avoid refetching with each tab change
export const useGetEarmarked = (
    params: StockManagementDetailsParams,
    enabled: boolean,
): UseQueryResult<any, any> => {
    const {
        earmarkedOrder: order,
        earmarkedPage: page,
        earmarkedPageSize: pageSize,
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
        queryKey: ['earmarked', queryString, id],
        queryFn: () => getEarmarked(id, queryString),
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

    const safeParams = useUrlParams(
        {
            order,
            page,
            pageSize,
            vaccine_stock,
        } as Partial<UrlParams>,
        {
            order: '-form_a_reception_date',
            pageSize: 20,
        },
    );

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
    const safeParams = useUrlParams(
        {
            order,
            page,
            pageSize,
            vaccine_stock,
        } as Partial<UrlParams>,
        {
            order: '-rrt_destruction_report_reception_date',
            pageSize: 20,
        },
    );
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
    const safeParams = useUrlParams(
        {
            order,
            page,
            pageSize,
            vaccine_stock,
        } as Partial<UrlParams>,
        {
            order: '-incident_report_received_by_rrt',
            pageSize: 20,
        },
    );
    const apiParams = useApiParams(safeParams);
    const queryString = new URLSearchParams(apiParams).toString();
    return useSnackQuery({
        queryKey: ['incidents', queryString, vaccine_stock],
        queryFn: () => getIncidentList(queryString),
        options: { ...options, enabled },
    });
};

const getEarmarkedList = async (queryString: string) => {
    return getRequest(`${modalUrl}earmarked_stock/?${queryString}`);
};

export const useGetEarmarkedList = (
    params: StockVariationParams,
    enabled: boolean,
): UseQueryResult<any, any> => {
    const {
        earmarkedOrder: order,
        earmarkedPage: page,
        earmarkedPageSize: pageSize,
        id: vaccine_stock,
    } = params;
    const safeParams = useUrlParams(
        {
            order,
            page,
            pageSize,
            vaccine_stock,
        } as Partial<UrlParams>,
        {
            order: '-created_at',
            pageSize: 20,
        },
    );
    const apiParams = useApiParams(safeParams);
    const queryString = new URLSearchParams(apiParams).toString();
    return useSnackQuery({
        queryKey: ['earmarked-list', queryString, vaccine_stock],
        queryFn: () => getEarmarkedList(queryString),
        options: { ...options, enabled },
    });
};

type UseCampaignOptionsResult = {
    roundOptions: DropdownOptions<string>[];
    campaignOptions: DropdownOptions<string>[];
    roundNumberOptions: DropdownOptions<string>[];
    isFetching: boolean;
};
// TODO get list of campaigns filtered by active vaccine
export const useCampaignOptions = (
    countryName: string,
    campaignName?: string,
): UseCampaignOptionsResult => {
    const { formatMessage } = useSafeIntl();
    const queryOptions = {
        select: data => {
            if (!data) return [];
            return data.filter(c => c.top_level_org_unit_name === countryName);
        },
        keepPreviousData: true,
        staleTime: 1000 * 60 * 15, // in MS
        cacheTime: 1000 * 60 * 5,
    };
    const { data, isFetching } = useGetCampaigns(
        {},
        CAMPAIGNS_ENDPOINT,
        undefined,
        queryOptions,
    );

    const roundOptions = useMemo(() => {
        const selectedCampaign = (data ?? []).find(
            campaign => campaign.obr_name === campaignName,
        );
        return selectedCampaign
            ? selectedCampaign.rounds.map(round => {
                  return {
                      label: `${formatMessage(MESSAGES.round)} ${round.number}`,
                      value: round.id,
                  };
              })
            : [];
    }, [campaignName, data, formatMessage]);

    const roundNumberOptions = useMemo(() => {
        const selectedCampaign = (data ?? []).find(
            campaign => campaign.obr_name === campaignName,
        );
        return selectedCampaign
            ? selectedCampaign.rounds.map(round => {
                  return {
                      label: `${formatMessage(MESSAGES.round)} ${round.number}`,
                      value: round.number,
                  };
              })
            : [];
    }, [campaignName, data, formatMessage]);

    const campaignOptions = useMemo(() => {
        const campaignsList = (data ?? []).map(c => {
            return {
                label: c.obr_name,
                value: c.obr_name,
            };
        });
        const defaultList = [{ label: campaignName, value: campaignName }];
        if ((campaignsList ?? []).length > 0) {
            return campaignsList;
        }
        if ((campaignsList ?? []).length === 0 && campaignName) {
            return defaultList;
        }
        return [];
    }, [campaignName, data]);

    return useMemo(() => {
        return {
            isFetching,
            campaignOptions,
            roundOptions,
            roundNumberOptions,
        };
    }, [campaignOptions, isFetching, roundOptions, roundNumberOptions]);
};

const createEditFormA = async (body: any) => {
    const copy = { ...body };
    const { lot_numbers } = body;
    if (lot_numbers && !Array.isArray(lot_numbers)) {
        const lotNumbersArray = commaSeparatedIdsToStringArray(lot_numbers);
        copy.lot_numbers = lotNumbersArray;
    }

    const filteredParams = copy
        ? Object.fromEntries(
              Object.entries(copy).filter(
                  ([key, value]) =>
                      value !== undefined &&
                      value !== null &&
                      key !== 'document',
              ),
          )
        : {};

    const requestBody: any = {
        url: `${modalUrl}outgoing_stock_movement/`,
        data: filteredParams,
    };

    if (copy?.document) {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars, no-unused-vars
        const { files, ...data } = filteredParams;
        const fileData = { files: copy.document };
        requestBody.data = data;
        requestBody.fileData = fileData;
    }

    if (body.id) {
        requestBody.url = `${modalUrl}outgoing_stock_movement/${body.id}/`;
        return patchRequest2(requestBody);
    }
    return postRequest2(requestBody);
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
            'document',
            'earmarked',
            'earmarked-list',
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

    const filteredParams = copy
        ? Object.fromEntries(
              Object.entries(copy).filter(
                  ([key, value]) =>
                      value !== undefined &&
                      value !== null &&
                      key !== 'document',
              ),
          )
        : {};

    const requestBody: any = {
        url: `${modalUrl}destruction_report/`,
        data: filteredParams,
    };

    if (copy?.document) {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars, no-unused-vars
        const { files, ...data } = filteredParams;
        const fileData = { files: copy.document };
        requestBody.data = data;
        requestBody.fileData = fileData;
    }

    if (body.id) {
        requestBody.url = `${modalUrl}destruction_report/${body.id}/`;
        return patchRequest2(requestBody);
    }
    return postRequest2(requestBody);
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
            'document',
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

    const filteredParams = copy
        ? Object.fromEntries(
              Object.entries(copy).filter(
                  ([key, value]) =>
                      value !== undefined &&
                      value !== null &&
                      key !== 'document',
              ),
          )
        : {};
    const requestBody: any = {
        url: `${modalUrl}incident_report/`,
        data: filteredParams,
    };

    if (copy?.document) {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars, no-unused-vars
        const { files, ...data } = filteredParams;
        const fileData = { files: copy.document };
        requestBody.data = data;
        requestBody.fileData = fileData;
    }

    if (body.id) {
        requestBody.url = `${modalUrl}incident_report/${body.id}/`;
        return patchRequest2(requestBody);
    }
    return postRequest2(requestBody);
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
            'document',
            'earmarked',
            'earmarked-list',
        ],
    });
};
const createEditEarmarked = (body: any) => {
    const copy = { ...body };

    const filteredParams = copy
        ? Object.fromEntries(
              Object.entries(copy).filter(
                  ([_key, value]) => value !== undefined && value !== null,
              ),
          )
        : {};

    const requestBody: any = {
        url: `${modalUrl}earmarked_stock/`,
        data: filteredParams,
    };

    if (body.id) {
        requestBody.url = `${modalUrl}earmarked_stock/${body.id}/`;
        return patchRequest2(requestBody);
    }
    return postRequest2(requestBody);
};

export const useSaveEarmarked = () => {
    return useSnackMutation({
        mutationFn: body => createEditEarmarked(body),
        invalidateQueryKey: [
            'vaccine-stock-list',
            'usable-vials',
            'stock-management-summary',
            'unusable-vials',
            'earmarked',
            'earmarked-list',
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

const deleteIncident = (id: string) => {
    return deleteRequest(`${modalUrl}incident_report/${id}`);
};

export const useDeleteIncident = (): UseMutationResult => {
    return useSnackMutation({
        mutationFn: deleteIncident,
        invalidateQueryKey: [
            'incidents',
            'vaccine-stock-list',
            'usable-vials',
            'stock-management-summary',
            'unusable-vials',
            'earmarked',
            'earmarked-list',
        ],
    });
};

const deleteDestruction = (id: string) => {
    return deleteRequest(`${modalUrl}destruction_report/${id}`);
};

export const useDeleteDestruction = (): UseMutationResult => {
    return useSnackMutation({
        mutationFn: deleteDestruction,
        invalidateQueryKey: [
            'destruction',
            'vaccine-stock-list',
            'usable-vials',
            'stock-management-summary',
            'unusable-vials',
        ],
    });
};

const deleteFormA = (id: string) => {
    return deleteRequest(`${modalUrl}outgoing_stock_movement/${id}`);
};

export const useDeleteFormA = (): UseMutationResult => {
    return useSnackMutation({
        mutationFn: deleteFormA,
        invalidateQueryKey: [
            'formA',
            'vaccine-stock-list',
            'usable-vials',
            'stock-management-summary',
            'unusable-vials',
            'earmarked',
            'earmarked-list',
        ],
    });
};
const deleteEarmarked = (id: string) => {
    return deleteRequest(`${modalUrl}earmarked_stock/${id}`);
};

export const useDeleteEarmarked = (): UseMutationResult => {
    return useSnackMutation({
        mutationFn: deleteEarmarked,
        invalidateQueryKey: [
            'vaccine-stock-list',
            'usable-vials',
            'stock-management-summary',
            'unusable-vials',
            'earmarked',
            'earmarked-list',
        ],
    });
};
