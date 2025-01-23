import { UseQueryResult } from 'react-query';
import { getRequest } from '../../../libs/Api';
import { useSnackQuery } from '../../../libs/apiHooks';

import MESSAGES from '../../instances/messages';
import { DataSourceVersionsSynchronizationDropdown } from '../types/dataSourceVersionsSynchronization';

export const getSearchDataSourceVersionsSynchronizationDropdown = async (
    searchTerm: string | undefined,
): Promise<DataSourceVersionsSynchronizationDropdown> => {
    const url = `/api/datasources/sync/?fields=id,name&name__icontains=${searchTerm}`;
    return getRequest(url).then(data => {
        if (!data) return [];
        return data.results.map(item => {
            return {
                value: item.id,
                label: item.name,
            };
        });
    });
};

export const useGetDataSourceVersionsSynchronizationDropdown = (
    id?: string,
): UseQueryResult<DataSourceVersionsSynchronizationDropdown[], Error> => {
    return useSnackQuery({
        queryKey: ['dataSourceVersionsSynchronizationDropdown', id],
        queryFn: () => {
            if (!id) return [];
            return getRequest(`/api/datasources/sync/${id}/?fields=id,name`);
        },
        snackErrorMsg: MESSAGES.error,
        options: {
            select: data => {
                if (data === undefined || (Array.isArray(data) && !data.length))
                    return [];
                return [
                    {
                        value: data.id,
                        label: data.name,
                    },
                ];
            },
        },
    });
};
