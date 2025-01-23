import { Box, Divider, Grid, Typography } from '@mui/material';
import { makeStyles } from '@mui/styles';
import {
    InputWithInfos,
    IntlFormatMessage,
    commonStyles,
    useSafeIntl,
    useSkipEffectOnMount,
} from 'bluesquare-components';
import React, {
    Dispatch,
    FunctionComponent,
    useCallback,
    useEffect,
    useMemo,
    useState,
} from 'react';

import DatesRange from '../../../components/filters/DatesRange';
import { ColorPicker } from '../../../components/forms/ColorPicker';
import InputComponent from '../../../components/forms/InputComponent';
import { LocationLimit } from '../../../utils/map/LocationLimit';
import { OrgUnitTreeviewModal } from './TreeView/OrgUnitTreeviewModal';

import { getChipColors } from '../../../constants/chipColors';

import { useCurrentUser } from '../../../utils/usersUtils';
import { useGetDataSources } from '../hooks/requests/useGetDataSources';
import { useGetGroupDropdown } from '../hooks/requests/useGetGroups';
import { useGetOrgUnit } from './TreeView/requests';

import { DropdownOptionsWithOriginal } from '../../../types/utils';
import { useGetProjectsDropDown } from '../../projects/hooks/requests/useGetProjectsDropDown';
import { useGetVersionLabel } from '../hooks/useGetVersionLabel';
import { useGetOrgUnitValidationStatus } from '../hooks/utils/useGetOrgUnitValidationStatus';
import { useInstancesOptions } from '../hooks/utils/useInstancesOptions';
import MESSAGES from '../messages';
import { useGetOrgUnitTypesDropdownOptions } from '../orgUnitTypes/hooks/useGetOrgUnitTypesDropdownOptions';
import { DataSource } from '../types/dataSources';
import { Search } from '../types/search';

type Props = {
    searches: [Search];
    locationLimit: number;
    setLocationLimit: Dispatch<React.SetStateAction<number>>;
    searchIndex: number;
    currentSearch: Search;
    setTextSearchError: Dispatch<React.SetStateAction<boolean>>;
    onSearch: () => void;
    onChangeColor: (color: string, index: number) => void;
    setSearches: React.Dispatch<React.SetStateAction<[Search]>>;
    currentTab: string;
    setHasLocationLimitError: React.Dispatch<React.SetStateAction<boolean>>;
};

const retrieveSourceFromVersionId = (
    versionId: string | number,
    dataSources: DropdownOptionsWithOriginal<DataSource>[],
): number | undefined => {
    const idAsNumber =
        typeof versionId === 'string' ? parseInt(versionId, 10) : versionId;
    const result = dataSources.find(dataSource =>
        dataSource.original.versions.some(version => version.id === idAsNumber),
    );
    return result?.original.id;
};
const useStyles = makeStyles(theme => ({
    ...commonStyles(theme),
}));

export const OrgUnitFilters: FunctionComponent<Props> = ({
    searches,
    searchIndex,
    currentSearch,
    onSearch,
    onChangeColor,
    setTextSearchError,
    setSearches,
    currentTab,
    setHasLocationLimitError,
    locationLimit,
    setLocationLimit,
}) => {
    // STATES
    const [dataSourceId, setDataSourceId] = useState<number | undefined>(
        currentSearch?.source ? parseInt(currentSearch?.source, 10) : undefined,
    );
    const [projectId, setProjectId] = useState<number | undefined>(
        currentSearch?.project,
    );
    const [sourceVersionId, setSourceVersionId] = useState<number | undefined>(
        currentSearch?.version
            ? parseInt(currentSearch?.version, 10)
            : undefined,
    );
    const [initialOrgUnitId, setInitialOrgUnitId] = useState<
        string | undefined
    >(currentSearch?.levels);
    const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);

    const [filters, setFilters] = useState<Record<string, any>>(currentSearch);
    // STATES

    // DATA
    const { data: initialOrgUnit } = useGetOrgUnit(initialOrgUnitId);
    const { data: dataSources, isFetching: isFetchingDataSources } =
        useGetDataSources(true);
    const { data: projects, isFetching: isFetchingProjects } =
        useGetProjectsDropDown();
    const { data: groups, isFetching: isFetchingGroups } = useGetGroupDropdown({
        dataSourceId,
        sourceVersionId,
    });
    const { data: orgUnitTypes, isFetching: isFetchingOrgUnitTypes } =
        useGetOrgUnitTypesDropdownOptions(projectId);
    const {
        data: validationStatusOptions,
        isLoading: isLoadingValidationStatusOptions,
    } = useGetOrgUnitValidationStatus(true);
    // DATA

    const getNewSourceVersionId = useCallback(
        (newDataSourceId: number) => {
            const dataSource = dataSources?.find(
                src => src?.original?.id === newDataSourceId,
            );
            const versions = dataSource?.original?.versions || [];
            return (
                dataSource?.original?.default_version?.id ||
                (versions.length > 0
                    ? versions[versions.length - 1]?.id
                    : undefined)
            );
        },
        [dataSources],
    );

    // EVENTS
    const handleChange = useCallback(
        (key, value) => {
            const newFilters: Record<string, unknown> = {
                ...filters,
            };
            if (key === 'version') {
                setSourceVersionId(parseInt(value, 10));
            }
            if (key === 'source') {
                setInitialOrgUnitId(undefined);
                const newDataSourceId = parseInt(value, 10);
                const newSourceVersionId =
                    getNewSourceVersionId(newDataSourceId);
                setSourceVersionId(newSourceVersionId);
                newFilters.version = newSourceVersionId?.toString();
                setDataSourceId(newDataSourceId);
                delete newFilters.levels;
                delete newFilters.orgUnitParentId;
            }
            if (key === 'levels') {
                setInitialOrgUnitId(value);
            }
            if (key === 'project') {
                setInitialOrgUnitId(undefined);
                newFilters.orgUnitTypeId = undefined;
                setProjectId(parseInt(value, 10));
            }
            if ((!value || value === '') && newFilters[key]) {
                delete newFilters[key];
            } else {
                newFilters[key] = value;
            }
            if (newFilters.source && newFilters.version) {
                delete newFilters.source;
            }
            setFilters(newFilters);
            const tempSearches: [Record<string, unknown>] = [...searches];
            tempSearches[searchIndex] = newFilters;
            setSearches(tempSearches);
        },
        [filters, searches, searchIndex, setSearches, getNewSourceVersionId],
    );

    const handleLocationLimitChange = useCallback(
        (key: string, value: number) => {
            setLocationLimit(value);
        },
        [setLocationLimit],
    );
    // EVENTS

    const currentColor = filters?.color
        ? `#${filters.color}`
        : getChipColors(searchIndex);

    // HOOKS
    const currentUser = useCurrentUser();
    const instancesOptions = useInstancesOptions();
    const getVersionLabel = useGetVersionLabel(dataSources);
    const classes: Record<string, string> = useStyles();
    const { formatMessage }: { formatMessage: IntlFormatMessage } =
        useSafeIntl();
    // HOOKS

    // USE EFFECTS
    useSkipEffectOnMount(() => {
        setInitialOrgUnitId(currentSearch?.levels);
    }, [currentSearch?.levels]);

    useSkipEffectOnMount(() => {
        if (filters !== currentSearch) {
            setFilters(currentSearch);
        }
    }, [currentSearch]);

    // Splitting this effect from the one below, so we can use the deps array
    useEffect(() => {
        // we may have a sourceVersionId but no dataSourceId if using deep linking
        // in that case we retrieve the dataSourceId so we can display it
        if (
            dataSources &&
            !dataSourceId &&
            filters?.version &&
            !filters?.group
        ) {
            const id = retrieveSourceFromVersionId(
                filters?.version,
                dataSources,
            );
            setDataSourceId(id);
            setSourceVersionId(parseInt(filters?.version, 10));
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [dataSourceId, dataSources, filters?.version]);

    useEffect(() => {
        if (!dataSourceId) {
            setDataSourceId(
                filters?.source ??
                    currentUser?.account?.default_version?.data_source?.id,
            );
            setSourceVersionId(
                filters?.version ?? currentUser?.account?.default_version?.id,
            );
        }
        if (dataSourceId && !sourceVersionId) {
            const newSourceVersionId = getNewSourceVersionId(dataSourceId);
            setSourceVersionId(newSourceVersionId);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // USE EFFECTS

    const versionsDropDown = useMemo(() => {
        if (!dataSources || !dataSourceId) return [];
        return (
            dataSources
                .filter(src => src.original?.id === dataSourceId)[0]
                ?.original?.versions.sort((a, b) => a.number - b.number)
                .map(version => ({
                    label: getVersionLabel(version.id),
                    value: version.id.toString(),
                })) ?? []
        );
    }, [dataSourceId, dataSources, getVersionLabel]);

    return (
        <Grid container spacing={2}>
            <Grid item xs={12} sm={4}>
                <Box mt={4} mb={2}>
                    <ColorPicker
                        currentColor={currentColor}
                        onChangeColor={color =>
                            onChangeColor(color, searchIndex)
                        }
                    />
                </Box>
                <InputWithInfos infos={formatMessage(MESSAGES.searchParams)}>
                    <InputComponent
                        keyValue="search"
                        onChange={handleChange}
                        value={filters.search}
                        type="search"
                        label={MESSAGES.search}
                        blockForbiddenChars
                        onEnterPressed={onSearch}
                        onErrorChange={hasError => setTextSearchError(hasError)}
                    />
                </InputWithInfos>
                <InputComponent
                    type="select"
                    disabled={isFetchingProjects}
                    keyValue="project"
                    onChange={handleChange}
                    value={!isFetchingProjects && projectId}
                    label={MESSAGES.project}
                    options={projects}
                    loading={isFetchingProjects}
                />
                <InputComponent
                    type="select"
                    disabled={isFetchingDataSources}
                    keyValue="source"
                    onChange={handleChange}
                    value={!isFetchingDataSources && dataSourceId}
                    label={MESSAGES.source}
                    options={dataSources}
                    loading={isFetchingDataSources}
                />

                {!showAdvancedSettings && (
                    <Typography
                        className={classes.advancedSettings}
                        variant="overline"
                        onClick={() => setShowAdvancedSettings(true)}
                    >
                        {formatMessage(MESSAGES.showAdvancedSettings)}
                    </Typography>
                )}
                {showAdvancedSettings && (
                    <>
                        <InputComponent
                            type="select"
                            disabled={isFetchingOrgUnitTypes}
                            keyValue="version"
                            onChange={handleChange}
                            value={sourceVersionId}
                            label={MESSAGES.sourceVersion}
                            options={versionsDropDown}
                            clearable={false}
                            loading={isFetchingOrgUnitTypes}
                        />
                        <InputComponent
                            type="number"
                            keyValue="depth"
                            onChange={handleChange}
                            value={filters?.depth}
                            label={MESSAGES.depth}
                            clearable
                        />
                        <Typography
                            className={classes.advancedSettings}
                            variant="overline"
                            onClick={() => setShowAdvancedSettings(false)}
                        >
                            {formatMessage(MESSAGES.hideAdvancedSettings)}
                        </Typography>
                    </>
                )}
            </Grid>

            <Grid item xs={12} sm={4}>
                <InputComponent
                    type="select"
                    multi
                    disabled={isFetchingOrgUnitTypes}
                    keyValue="orgUnitTypeId"
                    onChange={handleChange}
                    value={!isFetchingOrgUnitTypes && filters?.orgUnitTypeId}
                    label={MESSAGES.org_unit_type}
                    options={orgUnitTypes}
                    loading={isFetchingOrgUnitTypes}
                />
                <InputComponent
                    type="select"
                    multi
                    disabled={isFetchingGroups}
                    keyValue="group"
                    onChange={handleChange}
                    value={!isFetchingGroups && filters?.group}
                    label={MESSAGES.group}
                    options={groups}
                    loading={isFetchingGroups}
                />
                <InputComponent
                    type="select"
                    clearable={false}
                    keyValue="validation_status"
                    onChange={handleChange}
                    value={
                        isLoadingValidationStatusOptions
                            ? undefined
                            : filters?.validation_status
                    }
                    label={MESSAGES.validationStatus}
                    options={validationStatusOptions || []}
                    loading={isLoadingValidationStatusOptions}
                />

                <DatesRange
                    keyDateFrom="opening_date"
                    keyDateTo="closed_date"
                    onChangeDate={handleChange}
                    dateFrom={filters?.opening_date}
                    dateTo={filters?.closed_date}
                    labelFrom={MESSAGES.openingDate}
                    labelTo={MESSAGES.closingDate}
                />
                {currentTab === 'map' && (
                    <>
                        <Divider />
                        <Box mt={2}>
                            <LocationLimit
                                keyValue="locationLimit"
                                onChange={handleLocationLimitChange}
                                value={locationLimit}
                                setHasError={setHasLocationLimitError}
                            />
                        </Box>
                    </>
                )}
            </Grid>

            <Grid item xs={12} sm={4}>
                <Box mb={1}>
                    <OrgUnitTreeviewModal
                        toggleOnLabelClick={false}
                        titleMessage={MESSAGES.parent}
                        onConfirm={orgUnit => {
                            // TODO rename levels in to parent
                            handleChange('levels', orgUnit?.id);
                        }}
                        source={dataSourceId}
                        version={sourceVersionId}
                        initialSelection={initialOrgUnit}
                    />
                </Box>
                <Box mb={2}>
                    <InputComponent
                        type="select"
                        keyValue="geography"
                        onChange={handleChange}
                        value={filters?.geography}
                        label={MESSAGES.geographicalData}
                        options={[
                            {
                                label: formatMessage(MESSAGES.anyGeography),
                                value: 'any',
                            },
                            {
                                label: formatMessage(MESSAGES.withLocation),
                                value: 'location',
                            },
                            {
                                label: formatMessage(MESSAGES.withShape),
                                value: 'shape',
                            },
                            {
                                label: formatMessage(
                                    MESSAGES.noGeographicalData,
                                ),
                                value: 'none',
                            },
                        ]}
                    />
                </Box>
                <Box mt={1}>
                    <InputComponent
                        type="select"
                        keyValue="hasInstances"
                        onChange={handleChange}
                        value={filters?.hasInstances}
                        label={MESSAGES.hasInstances}
                        options={instancesOptions}
                    />
                </Box>
                {(filters?.hasInstances === 'true' ||
                    filters?.hasInstances === 'duplicates') && (
                    <DatesRange
                        onChangeDate={handleChange}
                        dateFrom={filters?.dateFrom}
                        dateTo={filters?.dateTo}
                    />
                )}
            </Grid>
        </Grid>
    );
};
