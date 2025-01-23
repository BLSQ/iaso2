import React, {
    FunctionComponent,
    useCallback,
    useEffect,
    useMemo,
    useState,
} from 'react';

import SearchIcon from '@mui/icons-material/Search';
import { Box, Button, Grid } from '@mui/material';
import { makeStyles } from '@mui/styles';

import {
    QueryBuilderInput,
    commonStyles,
    useHumanReadableJsonLogic,
    useRedirectTo,
    useSafeIntl,
} from 'bluesquare-components';

// @ts-ignore
import DatesRange from 'Iaso/components/filters/DatesRange';
// @ts-ignore
import { LocationLimit } from 'Iaso/utils/map/LocationLimit';
// @ts-ignore
import { UserOrgUnitRestriction } from 'Iaso/components/UserOrgUnitRestriction.tsx';
import InputComponent from '../../../components/forms/InputComponent';
import { OrgUnitTreeviewModal } from '../../orgUnits/components/TreeView/OrgUnitTreeviewModal';

import MESSAGES from '../messages';

import { baseUrl } from '../config';

import { useGetOrgUnit } from '../../orgUnits/components/TreeView/requests';
import { useGetGroupDropdown } from '../../orgUnits/hooks/requests/useGetGroups';
import { useGetTeamsDropdown } from '../../teams/hooks/requests/useGetTeams';
import {
    useGetBeneficiariesApiParams,
    useGetBeneficiaryTypesDropdown,
    useGetUsersDropDown,
} from '../hooks/requests';
import { useFiltersParams } from '../hooks/useFiltersParams';

import DownloadButtonsComponent from '../../../components/DownloadButtonsComponent';
import {
    SHOW_BENEFICIARY_TYPES_IN_LIST_MENU,
    hasFeatureFlag,
} from '../../../utils/featureFlags';
import { useCurrentUser } from '../../../utils/usersUtils';
import { Filters as FilterType, Params } from '../types/filters';

import { Popper } from '../../forms/fields/components/Popper';
import { useGetAllFormDescriptors } from '../../forms/fields/hooks/useGetFormDescriptor';
import { useGetQueryBuilderListToReplace } from '../../forms/fields/hooks/useGetQueryBuilderListToReplace';
import { useGetQueryBuilderFieldsForAllForms } from '../../forms/fields/hooks/useGetQueryBuildersFields';
import { useGetAllPossibleFields } from '../../forms/hooks/useGetPossibleFields';
import { parseJson } from '../../instances/utils/jsonLogicParse';

const useStyles = makeStyles(theme => ({
    ...commonStyles(theme),
}));

type Props = {
    params: Params;
    isFetching: boolean;
};

const Filters: FunctionComponent<Props> = ({ params, isFetching }) => {
    const getParams = useFiltersParams();
    const currentUser = useCurrentUser();
    const classes: Record<string, string> = useStyles();
    const { formatMessage } = useSafeIntl();
    const redirectTo = useRedirectTo();
    const [filters, setFilters] = useState<FilterType>({
        search: params.search,
        location: params.location,
        dateFrom: params.dateFrom,
        dateTo: params.dateTo,
        submitterId: params.submitterId,
        submitterTeamId: params.submitterTeamId,
        entityTypeIds: params.entityTypeIds,
        locationLimit: params.locationLimit,
        groups: params.groups,
        fieldsSearch: params.fieldsSearch,
    });

    useEffect(() => {
        setFilters({
            search: params.search,
            location: params.location,
            dateFrom: params.dateFrom,
            dateTo: params.dateTo,
            submitterId: params.submitterId,
            submitterTeamId: params.submitterTeamId,
            entityTypeIds: params.entityTypeIds,
            locationLimit: params.locationLimit,
            groups: params.groups,
            fieldsSearch: params.fieldsSearch,
        });
    }, [params]);
    const [filtersUpdated, setFiltersUpdated] = useState(false);
    const [initialOrgUnitId, setInitialOrgUnitId] = useState(params?.location);
    const [textSearchError, setTextSearchError] = useState<boolean>(false);

    const { data: initialOrgUnit } = useGetOrgUnit(initialOrgUnitId);

    const { data: types, isFetching: isFetchingTypes } =
        useGetBeneficiaryTypesDropdown();
    const { data: teamOptions } = useGetTeamsDropdown({});
    const selectedTeam = useMemo(() => {
        return teamOptions?.find(
            option => option.value === filters.submitterTeamId,
        )?.original;
    }, [filters.submitterTeamId, teamOptions]);

    const { data: usersOptions } = useGetUsersDropDown(selectedTeam);
    const dataSourceId = currentUser?.account?.default_version?.data_source?.id;
    const sourceVersionId = currentUser?.account?.default_version?.id;
    const { data: groups, isFetching: isFetchingGroups } = useGetGroupDropdown({
        dataSourceId,
        sourceVersionId,
    });

    // Load QueryBuilder resources
    const { allPossibleFields } = useGetAllPossibleFields();
    const { data: formDescriptors } = useGetAllFormDescriptors();
    const fields = useGetQueryBuilderFieldsForAllForms(
        formDescriptors,
        allPossibleFields,
    );
    const queryBuilderListToReplace = useGetQueryBuilderListToReplace();
    const getHumanReadableJsonLogic = useHumanReadableJsonLogic(
        fields,
        queryBuilderListToReplace,
    );
    const fieldsSearchJson = filters.fieldsSearch
        ? JSON.parse(filters.fieldsSearch)
        : undefined;

    const handleChangeQueryBuilder = value => {
        if (value) {
            const parsedValue = parseJson({ value, fields });
            handleChange('fieldsSearch', JSON.stringify(parsedValue));
        } else {
            handleChange('fieldsSearch', undefined);
        }
    };

    const handleSearch = useCallback(() => {
        if (filtersUpdated) {
            setFiltersUpdated(false);
            const tempParams: Params = getParams(params, filters);
            redirectTo(baseUrl, tempParams);
        }
    }, [filtersUpdated, getParams, params, filters, redirectTo]);

    const handleChange = useCallback(
        (key, value) => {
            setFiltersUpdated(true);
            if (key === 'location') {
                setInitialOrgUnitId(value);
            }
            setFilters({
                ...filters,
                [key]: value,
            });
        },
        [filters],
    );
    const handleTeamChange = useCallback(
        (key, value) => {
            setFiltersUpdated(true);
            setFilters({
                ...filters,
                [key]: value,
                submitterId: undefined,
            });
        },
        [filters],
    );

    const { url: apiUrl } = useGetBeneficiariesApiParams(params);
    return (
        <Box mb={1}>
            <UserOrgUnitRestriction />

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
                    {!hasFeatureFlag(
                        currentUser,
                        SHOW_BENEFICIARY_TYPES_IN_LIST_MENU,
                    ) && (
                        <InputComponent
                            keyValue="entityTypeIds"
                            onChange={handleChange}
                            value={filters.entityTypeIds}
                            type="select"
                            loading={isFetchingTypes}
                            label={MESSAGES.types}
                            options={types}
                            multi
                        />
                    )}

                    {hasFeatureFlag(
                        currentUser,
                        SHOW_BENEFICIARY_TYPES_IN_LIST_MENU,
                    ) && (
                        <InputComponent
                            type="select"
                            multi
                            disabled={isFetchingGroups}
                            keyValue="groups"
                            onChange={handleChange}
                            value={!isFetchingGroups && filters?.groups}
                            label={MESSAGES.groups}
                            options={groups}
                            loading={isFetchingGroups}
                        />
                    )}
                    <Box id="ou-tree-input">
                        <OrgUnitTreeviewModal
                            toggleOnLabelClick={false}
                            titleMessage={MESSAGES.location}
                            onConfirm={orgUnit =>
                                handleChange(
                                    'location',
                                    orgUnit ? orgUnit.id : undefined,
                                )
                            }
                            initialSelection={initialOrgUnit}
                        />
                    </Box>
                    {params.tab === 'map' && (
                        <Box mt={2}>
                            <LocationLimit
                                keyValue="locationLimit"
                                onChange={handleChange}
                                value={filters.locationLimit}
                            />
                        </Box>
                    )}
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <DatesRange
                        xs={12}
                        sm={12}
                        md={12}
                        lg={12}
                        onChangeDate={handleChange}
                        labelFrom={MESSAGES.dateFrom}
                        labelTo={MESSAGES.dateTo}
                        dateFrom={filters.dateFrom}
                        dateTo={filters.dateTo}
                    />
                    {!hasFeatureFlag(
                        currentUser,
                        SHOW_BENEFICIARY_TYPES_IN_LIST_MENU,
                    ) && (
                        <InputComponent
                            type="select"
                            multi
                            disabled={isFetchingGroups}
                            keyValue="groups"
                            onChange={handleChange}
                            value={!isFetchingGroups && filters?.groups}
                            label={MESSAGES.groups}
                            options={groups}
                            loading={isFetchingGroups}
                        />
                    )}
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <InputComponent
                        keyValue="submitterTeamId"
                        onChange={handleTeamChange}
                        value={filters.submitterTeamId}
                        type="select"
                        label={MESSAGES.submitterTeam}
                        options={teamOptions}
                    />
                    <InputComponent
                        keyValue="submitterId"
                        onChange={handleChange}
                        value={filters.submitterId}
                        type="select"
                        label={MESSAGES.submitter}
                        options={usersOptions}
                    />
                </Grid>
            </Grid>

            <Box mt={-2}>
                <Grid container columnSpacing={2}>
                    <Grid item xs={12} sm={6}>
                        <QueryBuilderInput
                            label={MESSAGES.queryBuilder}
                            onChange={handleChangeQueryBuilder}
                            initialLogic={fieldsSearchJson}
                            fields={fields}
                            iconProps={{
                                label: MESSAGES.queryBuilder,
                                value: getHumanReadableJsonLogic(
                                    fieldsSearchJson,
                                ),
                                onClear: () =>
                                    handleChange('fieldsSearch', undefined),
                            }}
                            InfoPopper={<Popper />}
                        />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                        <Box
                            mt={2}
                            display="flex"
                            justifyContent="flex-end"
                            alignItems="end"
                            flexDirection="column"
                        >
                            <Box mb={2}>
                                <Button
                                    data-test="search-button"
                                    disabled={
                                        textSearchError || !filtersUpdated
                                    }
                                    variant="contained"
                                    color="primary"
                                    onClick={() => handleSearch()}
                                >
                                    <SearchIcon
                                        className={classes.buttonIcon}
                                    />
                                    {formatMessage(MESSAGES.search)}
                                </Button>
                            </Box>
                            <DownloadButtonsComponent
                                csvUrl={`${apiUrl}&csv=true`}
                                xlsxUrl={`${apiUrl}&xlsx=true`}
                                disabled={isFetching}
                            />
                        </Box>
                    </Grid>
                </Grid>
            </Box>
        </Box>
    );
};

export { Filters };
