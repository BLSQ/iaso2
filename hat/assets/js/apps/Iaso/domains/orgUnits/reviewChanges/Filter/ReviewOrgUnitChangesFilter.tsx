import React, {
    FunctionComponent,
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
} from 'react';
import { Box, Grid, Typography } from '@mui/material';

import * as Permission from '../../../../utils/permissions';
import DatesRange from '../../../../components/filters/DatesRange';
import InputComponent from '../../../../components/forms/InputComponent';
import MESSAGES from '../messages';
import { ApproveOrgUnitParams } from '../types';
import { AsyncSelect } from '../../../../components/forms/AsyncSelect';
import { DisplayIfUserHasPerm } from '../../../../components/DisplayIfUserHasPerm';
import { DropdownOptions } from '../../../../types/utils';
import { FilterButton } from '../../../../components/FilterButton';
import { OrgUnitTreeviewModal } from '../../components/TreeView/OrgUnitTreeviewModal';
import { baseUrls } from '../../../../constants/urls';
import {
    getSearchDataSourceVersionsSynchronizationDropdown,
    useGetDataSourceVersionsSynchronizationDropdown,
} from '../../../dataSources/hooks/useGetDataSourceVersionsSynchronizationDropdown';
import { getUsersDropDown } from '../../../instances/hooks/requests/getUsersDropDown';
import { useDefaultSourceVersion } from '../../../dataSources/utils';
import { useFilterState } from '../../../../hooks/useFilterState';
import { useGetDataSources } from '../../hooks/requests/useGetDataSources';
import { useGetForms } from '../../../workflows/hooks/requests/useGetForms';
import { useGetGroupDropdown } from '../../hooks/requests/useGetGroups';
import { useGetOrgUnit } from '../../components/TreeView/requests';
import { useGetOrgUnitTypesDropdownOptions } from '../../orgUnitTypes/hooks/useGetOrgUnitTypesDropdownOptions';
import { useGetProfilesDropdown } from '../../../instances/hooks/useGetProfilesDropdown';
import { useGetProjectsDropdownOptions } from '../../../projects/hooks/requests';
import { useGetUserRolesDropDown } from '../../../userRoles/hooks/requests/useGetUserRoles';
import { useGetVersionLabel } from '../../hooks/useGetVersionLabel';
import { usePaymentStatusOptions } from '../hooks/api/useGetPaymentStatusOptions';
import { useRedirectToReplace, useSafeIntl } from 'bluesquare-components';

const baseUrl = baseUrls.orgUnitsChangeRequest;

type Props = {
    params: ApproveOrgUnitParams;
};

const styles = {
    advancedSettings: {
        color: theme => theme.palette.primary.main,
        alignSelf: 'center',
        textAlign: 'right',
        flex: '1',
        cursor: 'pointer',
    },
};

export const ReviewOrgUnitChangesFilter: FunctionComponent<Props> = ({
    params,
}) => {
    const redirectToReplace = useRedirectToReplace();

    const defaultSourceVersion = useDefaultSourceVersion();
    const [selectedVersionId, setSelectedVersionId] = useState<string>(
        params.source_version_id
            ? params.source_version_id
            : defaultSourceVersion.version.id.toString(),
    );

    const { filters, handleSearch, handleChange, filtersUpdated } =
        useFilterState({ baseUrl, params });
    const { data: dataSources, isFetching: isFetchingDataSources } =
        useGetDataSources(true);
    const { data: initialOrgUnit } = useGetOrgUnit(params.parent_id);
    const { data: orgUnitTypeOptions, isLoading: isLoadingTypes } =
        useGetOrgUnitTypesDropdownOptions();
    const { data: forms, isFetching: isLoadingForms } = useGetForms();
    const { data: selectedUsers } = useGetProfilesDropdown(filters.userIds);
    const { data: userRoles, isFetching: isFetchingUserRoles } =
        useGetUserRolesDropDown();

    const { data: allProjects, isFetching: isFetchingProjects } =
        useGetProjectsDropdownOptions();
    const { data: paymentStatuses, isFetching: isFetchingPaymentStatuses } =
        usePaymentStatusOptions();

    const updateParams = (paramsToUpdate, selectedVersion) => {
        const newParams = {
            ...paramsToUpdate,
            source_version_id: selectedVersion,
        };
        return newParams;
    };

    // Redirect to default version
    useEffect(() => {
        if (!params.source_version_id) {
            const updatedParams = updateParams(params, selectedVersionId);
            redirectToReplace(baseUrl, updatedParams);
        }
    }, [selectedVersionId, redirectToReplace, params]);

    // Get the source when the source_version_id exists
    const sourceParam = useMemo(
        () =>
            params.source_version_id
                ? dataSources?.filter(source =>
                      source.original.versions.some(
                          version =>
                              version.id.toString() ===
                              params.source_version_id,
                      ),
                  )[0].value
                : undefined,
        [dataSources, params.source_version_id],
    );

    const [dataSource, setDataSource] = useState<string>(
        sourceParam || defaultSourceVersion.source.id.toString(),
    );
    const formOptions = useMemo(
        () =>
            forms?.map(form => ({
                label: form.name,
                value: form.id,
            })) || [],
        [forms],
    );
    // Get the initial data source id
    const initialDataSource = useMemo(
        () =>
            dataSources?.find(
                source =>
                    source.value === defaultSourceVersion.source.id.toString(),
            )?.value || '',
        [dataSources, defaultSourceVersion.source.id],
    );

    const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);
    const { formatMessage } = useSafeIntl();

    const { data: groupOptions, isLoading: isLoadingGroups } =
        useGetGroupDropdown(
            selectedVersionId ? { defaultVersion: selectedVersionId } : {},
        );

    // Change the selected dataSource
    useEffect(() => {
        const updatedDataSource =
            sourceParam ||
            dataSources?.find(
                source =>
                    source.value === defaultSourceVersion.source.id.toString(),
            )?.value;

        if (updatedDataSource) {
            setDataSource(updatedDataSource as unknown as string);
        }
    }, [
        dataSources,
        defaultSourceVersion.source.id,
        setDataSource,
        sourceParam,
    ]);

    const statusOptions: DropdownOptions<string>[] = useMemo(
        () => [
            {
                label: formatMessage(MESSAGES.new),
                value: 'new',
            },
            {
                label: formatMessage(MESSAGES.rejected),
                value: 'rejected',
            },
            {
                label: formatMessage(MESSAGES.approved),
                value: 'approved',
            },
        ],
        [formatMessage],
    );
    const handleChangeUsers = useCallback(
        (keyValue, newValue) => {
            const joined = newValue?.map(r => r.value)?.join(',');
            handleChange(keyValue, joined);
        },
        [handleChange],
    );

    // Handle Data Source Versions Synchronization.
    // If the `data_source_synchronization_id` URL param exists, fetch the corresponding item.
    const {
        data: dataSourceVersionsSynchronization,
        isLoading: isLoadingDataSourceVersionsSynchronization,
    } = useGetDataSourceVersionsSynchronizationDropdown(
        filters.data_source_synchronization_id,
    );
    const handleChangeDataSourceVersionsSynchronization = useCallback(
        (keyValue, dataSourceVersionsSynchronization) => {
            const id: number = dataSourceVersionsSynchronization?.value;
            // Set the value of `data_source_synchronization_id` URL param.
            handleChange(keyValue, id);
        },
        [handleChange],
    );

    // handle dataSource and sourceVersion change
    const handleDataSourceVersionChange = useCallback(
        (key, newValue) => {
            let selectedVersion = null;
            if (key === 'source') {
                setDataSource(newValue);
                const selectedSource = dataSources?.filter(
                    source => source.value === newValue,
                )[0];

                selectedVersion =
                    selectedSource?.original?.default_version.id.toString();
            } else {
                selectedVersion = newValue.toString();
            }
            // Reset the group filter state
            handleChange('groups', null);
            filters.groups = null;

            // Reset selected version
            setSelectedVersionId(selectedVersion || '');
            if (selectedVersion) {
                handleChange('source_version_id', selectedVersion);
            }
            // Reset the parent_id
            filters.parent_id = null;
        },
        [dataSources, filters, handleChange],
    );

    const getVersionLabel = useGetVersionLabel(dataSources);
    // Get the versions dropdown options based on the selected dataSource
    const versionsDropDown = useMemo(() => {
        if (!dataSources || !dataSource) return [];
        return (
            dataSources
                .filter(
                    src => (src.value as unknown as string) === dataSource,
                )[0]
                ?.original?.versions.sort((a, b) => a.number - b.number)
                .map(version => ({
                    label: getVersionLabel(version.id),
                    value: version.id.toString(),
                })) ?? []
        );
    }, [dataSource, dataSources, getVersionLabel]);
    // Reset the OrgUnitTreeviewModal when the sourceVersion changed
    const sourceTreeviewResetControl = useRef(selectedVersionId);
    useEffect(() => {
        if (sourceTreeviewResetControl.current !== selectedVersionId) {
            sourceTreeviewResetControl.current = selectedVersionId;
        }
    }, [selectedVersionId]);

    return (
        <Grid container spacing={2}>
            <Grid item xs={12} md={4} lg={3}>
                <InputComponent
                    keyValue="projectIds"
                    onChange={handleChange}
                    value={filters.projectIds}
                    type="select"
                    options={allProjects}
                    label={MESSAGES.projects}
                    loading={isFetchingProjects}
                    onEnterPressed={handleSearch}
                    clearable
                    multi
                />
                <InputComponent
                    type="select"
                    multi
                    clearable
                    keyValue="status"
                    value={filters.status}
                    onChange={handleChange}
                    options={statusOptions}
                    labelString={formatMessage(MESSAGES.status)}
                />
                <InputComponent
                    type="select"
                    multi
                    clearable
                    keyValue="groups"
                    value={filters.groups}
                    onChange={handleChange}
                    options={groupOptions}
                    loading={isLoadingGroups}
                    labelString={formatMessage(MESSAGES.group)}
                />
                <Box mt={2}>
                    <InputComponent
                        type="select"
                        disabled={isFetchingDataSources}
                        keyValue="source"
                        onChange={handleDataSourceVersionChange}
                        value={isFetchingDataSources ? '' : dataSource}
                        label={MESSAGES.source}
                        options={dataSources}
                        loading={isFetchingDataSources}
                    />
                    {!showAdvancedSettings && (
                        <Typography
                            data-test="advanced-settings"
                            variant="overline"
                            sx={styles.advancedSettings}
                            onClick={() => setShowAdvancedSettings(true)}
                        >
                            {formatMessage(MESSAGES.showAdvancedSettings)}
                        </Typography>
                    )}
                    {showAdvancedSettings && (
                        <>
                            <InputComponent
                                type="select"
                                disabled={isFetchingDataSources}
                                keyValue="version"
                                onChange={handleDataSourceVersionChange}
                                value={selectedVersionId || ''}
                                label={MESSAGES.sourceVersion}
                                options={versionsDropDown}
                                clearable={false}
                                loading={isFetchingDataSources}
                            />

                            <Box ml={1}>
                                <Typography
                                    data-test="advanced-settings"
                                    variant="overline"
                                    onClick={() =>
                                        setShowAdvancedSettings(false)
                                    }
                                >
                                    {formatMessage(
                                        MESSAGES.hideAdvancedSettings,
                                    )}
                                </Typography>
                            </Box>
                        </>
                    )}
                </Box>
            </Grid>
            <Grid item xs={12} md={4} lg={3}>
                <Box id="ou-tree-input">
                    <OrgUnitTreeviewModal
                        toggleOnLabelClick={false}
                        titleMessage={MESSAGES.parent}
                        source={
                            dataSource
                                ? dataSource.toString()
                                : initialDataSource.toString()
                        }
                        version={selectedVersionId}
                        onConfirm={orgUnit => {
                            handleChange('parent_id', orgUnit?.id);
                        }}
                        initialSelection={initialOrgUnit}
                        resetTrigger={
                            sourceTreeviewResetControl.current !==
                            selectedVersionId
                        }
                    />
                </Box>
                <InputComponent
                    type="select"
                    multi
                    clearable
                    keyValue="org_unit_type_id"
                    value={filters.org_unit_type_id}
                    onChange={handleChange}
                    loading={isLoadingTypes}
                    options={orgUnitTypeOptions}
                    labelString={formatMessage(MESSAGES.orgUnitType)}
                />
                <InputComponent
                    type="select"
                    multi
                    clearable
                    keyValue="forms"
                    value={filters.forms}
                    onChange={handleChange}
                    options={formOptions}
                    loading={isLoadingForms}
                    labelString={formatMessage(MESSAGES.forms)}
                />
                <DisplayIfUserHasPerm
                    permissions={[
                        Permission.SOURCE_WRITE,
                        Permission.ORG_UNITS_CHANGE_REQUESTS_CONFIGURATION,
                        Permission.ORG_UNITS,
                    ]}
                    strict={true}
                >
                    <Box mt={2}>
                        <AsyncSelect
                            keyValue="data_source_synchronization_id"
                            clearable
                            label={MESSAGES.dataSourceVersionsSynchronization}
                            value={dataSourceVersionsSynchronization ?? ''}
                            loading={isLoadingDataSourceVersionsSynchronization}
                            onChange={
                                handleChangeDataSourceVersionsSynchronization
                            }
                            debounceTime={500}
                            fetchOptions={input =>
                                getSearchDataSourceVersionsSynchronizationDropdown(
                                    input,
                                )
                            }
                        />
                    </Box>
                </DisplayIfUserHasPerm>
            </Grid>
            <Grid item xs={12} md={4} lg={3}>
                <Box mt={2}>
                    <AsyncSelect
                        keyValue="userIds"
                        label={MESSAGES.user}
                        value={selectedUsers ?? ''}
                        onChange={handleChangeUsers}
                        debounceTime={500}
                        multi
                        fetchOptions={input => getUsersDropDown(input)}
                    />
                </Box>
                <InputComponent
                    type="select"
                    multi
                    clearable
                    keyValue="userRoles"
                    value={filters.userRoles}
                    onChange={handleChange}
                    loading={isFetchingUserRoles}
                    options={userRoles}
                    labelString={formatMessage(MESSAGES.userRoles)}
                />
                <InputComponent
                    keyValue="withLocation"
                    clearable
                    onChange={handleChange}
                    value={filters.withLocation || null}
                    type="select"
                    options={[
                        {
                            label: formatMessage(MESSAGES.with),
                            value: 'true',
                        },
                        {
                            label: formatMessage(MESSAGES.without),
                            value: 'false',
                        },
                    ]}
                />
                <InputComponent
                    label={MESSAGES.location}
                    type="select"
                    clearable
                    keyValue="paymentStatus"
                    value={filters.paymentStatus}
                    onChange={handleChange}
                    loading={isFetchingPaymentStatuses}
                    options={paymentStatuses}
                    labelString={formatMessage(MESSAGES.paymentStatus)}
                />
            </Grid>

            <Grid item xs={12} md={4} lg={3}>
                <DatesRange
                    xs={12}
                    sm={12}
                    md={12}
                    lg={12}
                    keyDateFrom="created_at_after"
                    keyDateTo="created_at_before"
                    onChangeDate={handleChange}
                    dateFrom={filters.created_at_after}
                    dateTo={filters.created_at_before}
                    labelFrom={MESSAGES.createdDateFrom}
                    labelTo={MESSAGES.createdDateTo}
                />
                <Box mt={2} display="flex" justifyContent="flex-end">
                    <FilterButton
                        disabled={!filtersUpdated}
                        onFilter={handleSearch}
                    />
                </Box>
            </Grid>
        </Grid>
    );
};
