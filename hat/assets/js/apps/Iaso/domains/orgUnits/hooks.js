import { getRequest, patchRequest, postRequest } from 'Iaso/libs/Api.ts';
import {
    useSnackMutation,
    useSnackQueries,
    useSnackQuery,
} from 'Iaso/libs/apiHooks.ts';
import { useCallback, useMemo } from 'react';
import { useQueryClient } from 'react-query';
import { getChipColors, getOtChipColors } from '../../constants/chipColors';
import { useCheckUserHasWriteTypePermission } from '../../utils/usersUtils.ts';
import MESSAGES from './messages.ts';

export const useOrgUnitDetailData = (
    isNewOrgunit,
    orgUnitId,
    setCurrentOrgUnit,
    levels,
    tab,
) => {
    const { data: originalOrgUnit, isFetching: isFetchingDetail } =
        useSnackQuery(
            ['currentOrgUnit', orgUnitId],
            () => getRequest(`/api/orgunits/${orgUnitId}/`),
            MESSAGES.fetchOrgUnitError,
            {
                enabled: !isNewOrgunit,
                onSuccess: ou => setCurrentOrgUnit(ou),
            },
        );
    const groupsDataSourceQueryParams = originalOrgUnit?.source_id
        ? `?dataSource=${originalOrgUnit.source_id}`
        : undefined;
    const groupsQueryParams = isNewOrgunit
        ? '?defaultVersion=true'
        : groupsDataSourceQueryParams;
    const groupsApiUrl = '/api/groups/dropdown/';

    const cacheOptions = {
        staleTime: 1000 * 60 * 15, // in MS
        cacheTime: 1000 * 60 * 5,
    };
    const checkUserHasWriteTypePermission =
        useCheckUserHasWriteTypePermission();
    // Filter org unit types based on user permissions and editable types
    // Include types the user can edit, plus the current org unit's type
    const onSelectOrgUnitTypes = useCallback(
        data => {
            const orgUnitTypes =
                data?.orgUnitTypes.map((ot, i) => ({
                    ...ot,
                    color: getOtChipColors(i),
                })) || [];
            return orgUnitTypes.filter(
                ot =>
                    checkUserHasWriteTypePermission(ot.id) ||
                    originalOrgUnit?.org_unit_type?.id === ot.id,
            );
        },
        [checkUserHasWriteTypePermission, originalOrgUnit?.org_unit_type?.id],
    );
    const [
        { data: groups = [], isFetching: isFetchingGroups },
        { data: orgUnitTypes = [], isFetching: isFetchingOrgUnitTypes },
        { data: links = [], isFetching: isFetchingLinks },
        {
            data: associatedDataSources = [],
            isFetching: isFetchingAssociatedDataSources,
        },
        { data: sources = [], isFetching: isFetchingPlainSources },
        { data: parentOrgUnit },
    ] = useSnackQueries([
        {
            queryKey: ['groups', groupsQueryParams],
            queryFn: () => getRequest(`${groupsApiUrl}${groupsQueryParams}`),
            snackErrorMsg: MESSAGES.fetchGroupsError,
            options: {
                select: data =>
                    data.map(group => ({
                        value: group.id,
                        label: group.label,
                    })),
                enabled:
                    (tab === 'children' || tab === 'infos') &&
                    (Boolean(originalOrgUnit) || isNewOrgunit),
                ...cacheOptions,
            },
        },
        {
            queryKey: ['orgUnitTypes'],
            queryFn: () => getRequest('/api/v2/orgunittypes/'),
            snackErrorMsg: MESSAGES.fetchOrgUnitTypesError,
            options: {
                select: onSelectOrgUnitTypes,
                enabled: tab === 'map' || tab === 'children' || tab === 'infos',
                ...cacheOptions,
            },
        },
        {
            queryKey: ['links'],
            queryFn: () => getRequest(`/api/links/?orgUnitId=${orgUnitId}`),
            snackErrorMsg: MESSAGES.fetchLinksError,
            options: {
                select: data => data.links,
                enabled: !isNewOrgunit,
            },
        },
        {
            queryKey: ['associatedDataSources'],
            queryFn: () =>
                getRequest(`/api/datasources/?linkedTo=${orgUnitId}`),
            snackErrorMsg: MESSAGES.fetchSourcesError,
            options: {
                select: data =>
                    data.sources.map((s, i) => ({
                        ...s,
                        color: getChipColors(i),
                    })),
                enabled: !isNewOrgunit && (tab === 'map' || tab === 'links'),
                ...cacheOptions,
            },
        },
        // FIXME this can probably be refactored into a single query
        {
            queryKey: ['associatedDataSources'],
            queryFn: () => getRequest('/api/datasources/'),
            snackErrorMsg: MESSAGES.fetchSourcesError,
            options: {
                select: data =>
                    data.sources.map((s, i) => ({
                        ...s,
                        color: getChipColors(i),
                    })),
                // here seems to be an error here as the condition for enabling is the same as the query above
                enabled: isNewOrgunit && (tab === 'map' || tab === 'links'),
                ...cacheOptions,
            },
        },
        {
            queryKey: ['parentOrgUnit', orgUnitId],
            queryFn: () => getRequest(`/api/orgunits/${levels}/`),
            snackErrorMsg: MESSAGES.fetchOrgUnitError,
            options: {
                enabled:
                    Boolean(levels) &&
                    isNewOrgunit &&
                    levels.split(',').length === 1,

                ...cacheOptions,
            },
        },
    ]);

    const isFetchingSources = isNewOrgunit
        ? isFetchingPlainSources
        : isFetchingAssociatedDataSources;

    return {
        groups,
        orgUnitTypes,
        links,
        isFetchingDatas:
            isFetchingGroups ||
            isFetchingSources ||
            isFetchingLinks ||
            isFetchingOrgUnitTypes,
        sources: isNewOrgunit ? sources : associatedDataSources,
        originalOrgUnit,
        isFetchingDetail,
        isFetchingOrgUnitTypes,
        isFetchingGroups,
        isFetchingSources,
        parentOrgUnit,
    };
};

export const useSaveOrgUnit = (onSuccess, invalidateQueryKey) =>
    useSnackMutation(
        body =>
            body.id
                ? patchRequest(`/api/orgunits/${body.id}/`, body)
                : postRequest('/api/orgunits/create_org_unit/', body),
        MESSAGES.saveOrgUnitSuccesfull,
        MESSAGES.saveOrgUnitError,
        invalidateQueryKey,
        { onSuccess },
    );

export const useRefreshOrgUnit = () => {
    const queryClient = useQueryClient();
    return data => queryClient.setQueryData(['forms', data.id], data);
};

export const useOrgUnitTabParams = (params, paramsPrefix) => {
    return useMemo(() => {
        const { orgUnitId, tab, ...rest } = params;
        const tabParams = { orgUnitId, tab };
        const formKeys = Object.keys(rest).filter(k =>
            k.includes(paramsPrefix),
        );
        formKeys.forEach(formKey => {
            tabParams[formKey] = rest[formKey];
        });
        return tabParams;
    }, [params, paramsPrefix]);
};
