import React, {
    FunctionComponent,
    useState,
    useMemo,
    useCallback,
} from 'react';
import { Grid, Button } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { useSafeIntl } from 'bluesquare-components';
import { useGetProjectsDropdownOptions } from '../../../projects/hooks/requests';
import { useDataSourceVersions } from '../../../dataSources/requests';
import { useGetDataSources } from '../../../dataSources/useGetDataSources';
import { useFilterState } from '../../../../hooks/useFilterState';
import InputComponent from '../../../../components/forms/InputComponent';
import { baseUrl } from '../config';
import MESSAGES from '../messages';

type Params = {
    page?: string;
    search?: string;
    dataSource?: string;
    version?: string;
    project_ids?: string;
    accountId: string;
};

type Props = {
    params: Params;
};

const dataSourceByProjectId = (dataSources: any[], projectId: string) => {
    const allDataSource: any[] = dataSources?.map(
        (source: { projects: any[][]; name: any; id: any }) => {
            const projectIds = source?.projects[0].map(
                (project: { id: string }) => project?.id.toString(),
            );
            return {
                label: source?.name,
                value: `${source?.id}`,
                projectIds,
            };
        },
    );
    if (projectId) {
        return allDataSource?.filter((source: { projectIds: string[] }) =>
            source.projectIds?.includes(projectId),
        );
    }
    return allDataSource;
};

const versionsBySource = (sourceVersions: any[], source: string) => {
    const versions = sourceVersions?.filter(
        version => version?.data_source.toString() === source,
    );
    return versions?.map(version => {
        return {
            label: `${version?.data_source_name}-${version?.number}`,
            value: `${version?.id}`,
        };
    });
};

const Filters: FunctionComponent<Props> = ({ params }) => {
    const { filters, handleSearch, handleChange, filtersUpdated } =
        useFilterState({ baseUrl, params, withPagination: true });

    const [textSearchError, setTextSearchError] = useState<boolean>(false);

    const { data: projects, isFetching: isFetchingProjects } =
        useGetProjectsDropdownOptions();
    const { data: dataSources, isLoading: areSourcesLoading } =
        useGetDataSources({ ...params, ...filters });

    const { data: sourceVersions, isLoading: areSourceVersionsLoading } =
        useDataSourceVersions();

    const [projectIds, setProjectIds] = useState<string | undefined>(
        filters?.project_ids,
    );
    const [dataSource, setDataSource] = useState<string | undefined>(
        filters?.dataSource,
    );
    const [version, setVersion] = useState<string | undefined>(
        filters?.version,
    );

    const dataSourceDropDown = useMemo(
        () => dataSourceByProjectId(dataSources?.sources, filters?.project_ids),
        [dataSources, filters?.project_ids],
    );

    const sourceVersionsDropDown = useMemo(
        () => versionsBySource(sourceVersions, filters?.dataSource),
        [filters?.dataSource, sourceVersions],
    );

    const handleChangeSelect = useCallback(
        (key, newValue) => {
            let value = newValue;

            if (newValue === null) {
                value = undefined;
            }
            if (key === 'project_ids') {
                filters.dataSource = undefined;
                filters.version = undefined;
                setProjectIds(value);
                setDataSource(undefined);
                setVersion(undefined);
            }
            if (key === 'dataSource') {
                filters.version = undefined;
                setVersion(undefined);
                setDataSource(value);
            } else if (key === 'version') {
                setVersion(value);
            }
            handleChange(key, value);
        },
        [filters, handleChange, setProjectIds, setDataSource, setVersion],
    );
    const { formatMessage } = useSafeIntl();

    return (
        <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
                <InputComponent
                    keyValue="search"
                    onChange={handleChange}
                    value={filters.search}
                    type="search"
                    label={MESSAGES.search}
                    onEnterPressed={handleSearch}
                    blockForbiddenChars
                    onErrorChange={setTextSearchError}
                />
            </Grid>
            <Grid item xs={12} md={3}>
                <InputComponent
                    keyValue="project_ids"
                    onChange={handleChangeSelect}
                    value={projectIds}
                    type="select"
                    label={MESSAGES.projects}
                    options={projects}
                    loading={isFetchingProjects}
                    blockForbiddenChars
                    onEnterPressed={handleSearch}
                    onErrorChange={setTextSearchError}
                />
            </Grid>

            <Grid item xs={12} md={3}>
                <InputComponent
                    keyValue="dataSource"
                    onChange={handleChangeSelect}
                    value={dataSource}
                    type="select"
                    label={MESSAGES.dataSource}
                    options={dataSourceDropDown}
                    loading={areSourcesLoading}
                    blockForbiddenChars
                    onEnterPressed={handleSearch}
                    onErrorChange={setTextSearchError}
                />
            </Grid>

            <Grid item xs={12} md={3}>
                <InputComponent
                    keyValue="version"
                    onChange={handleChangeSelect}
                    value={version}
                    type="select"
                    label={MESSAGES.sourceVersion}
                    options={sourceVersionsDropDown}
                    loading={areSourceVersionsLoading}
                    blockForbiddenChars
                    onEnterPressed={handleSearch}
                    onErrorChange={setTextSearchError}
                />
            </Grid>

            <Grid container item xs={12} md={12} justifyContent="flex-end">
                <Button
                    data-test="search-button"
                    disabled={!filtersUpdated || textSearchError}
                    variant="contained"
                    color="primary"
                    onClick={() => handleSearch()}
                >
                    <SearchIcon />
                    {formatMessage(MESSAGES.search)}
                </Button>
            </Grid>
        </Grid>
    );
};
export { Filters };
