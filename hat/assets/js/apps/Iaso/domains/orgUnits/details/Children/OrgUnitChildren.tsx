import { Box } from '@mui/material';
import React, { FunctionComponent, useMemo } from 'react';
import DownloadButtonsComponent from '../../../../components/DownloadButtonsComponent';
import { OU_CHILDREN_PREFIX } from '../../../../constants/urls';
import { DropdownOptions } from '../../../../types/utils';
import { useGetOrgUnitChildren } from '../../hooks/requests/useGetOrgUnitChildren';
import { OrgUnitChildrenFilters } from './OrgUnitChildrenFilters';
import { OrgUnitChildrenTable } from './OrgUnitChildrenTable';
import { useOrgUnitChildrenQueryString } from './useOrgUnitChildrenQueryString';

const apiUrl = '/api/orgunits';

type Props = {
    params: any;
    baseUrl: string;
    groups?: DropdownOptions<string>[];
};

export const OrgUnitChildren: FunctionComponent<Props> = ({
    params,
    baseUrl,
    groups,
}) => {
    // Add deafult value "all" for validation status
    const paramsWithDefaultValue = useMemo(() => {
        const copy = { ...params };
        if (params[`${OU_CHILDREN_PREFIX}Validation_status`] === undefined) {
            copy[`${OU_CHILDREN_PREFIX}Validation_status`] = 'all';
        }
        return copy;
    }, [params]);
    // Generate the queryString here so it can be used for the download urls
    const queryString = useOrgUnitChildrenQueryString(paramsWithDefaultValue);
    const { data, isFetching: loading } = useGetOrgUnitChildren(queryString);
    const csvUrl = `${apiUrl}/?${queryString}&csv=true`;
    const xlsxUrl = `${apiUrl}/?${queryString}&xlsx=true`;
    const gpkgUrl = `${apiUrl}/?${queryString}&gpkg=true`;
    return (
        <>
            <OrgUnitChildrenFilters
                baseUrl={baseUrl}
                params={paramsWithDefaultValue}
                groups={groups}
            />
            {Boolean(data?.orgunits?.length) && (
                <Box
                    mt={2}
                    display="inline-flex"
                    justifyContent="flex-end"
                    style={{ width: '100%' }}
                >
                    <DownloadButtonsComponent
                        csvUrl={csvUrl}
                        xlsxUrl={xlsxUrl}
                        gpkgUrl={gpkgUrl}
                        disabled={loading}
                    />
                </Box>
            )}
            <OrgUnitChildrenTable
                baseUrl={baseUrl}
                params={paramsWithDefaultValue}
                paramsPrefix={OU_CHILDREN_PREFIX}
                data={data}
                loading={loading}
            />
        </>
    );
};
