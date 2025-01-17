import { getRequest } from '../../../libs/Api';

export const getDataSourceVersionsSynchronisationDropdown = async (
    searchTerm: string | undefined,
): Promise<any> => {
    const url = `/api/datasources/sync/?fields=id,name&name__icontains=${searchTerm}`;
    return getRequest(url).then(data => {
        return data.results.map(item => {
            return {
                value: item.id,
                label: item.name,
            };
        });
    });
};
