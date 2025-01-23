import { Box, Grid } from '@mui/material';
import React, { FunctionComponent, useCallback, useState } from 'react';
import InputComponent from '../../../../components/forms/InputComponent';
import { SearchButton } from '../../../../components/SearchButton';
import { OU_CHILDREN_PREFIX } from '../../../../constants/urls';
import { useFilterState } from '../../../../hooks/useFilterState';
import { DropdownOptions } from '../../../../types/utils';
import { useGetOrgUnitValidationStatus } from '../../hooks/utils/useGetOrgUnitValidationStatus';
import { useInstancesOptions } from '../../hooks/utils/useInstancesOptions';
import { useLocationOptions } from '../../hooks/utils/useLocationOptions';
import MESSAGES from '../../messages';
import { useGetOrgUnitTypesDropdownOptions } from '../../orgUnitTypes/hooks/useGetOrgUnitTypesDropdownOptions';

type Props = {
    params: any;
    baseUrl: string;
    groups?: DropdownOptions<string>[];
};

export const OrgUnitChildrenFilters: FunctionComponent<Props> = ({
    params,
    baseUrl,
    groups = [],
}) => {
    const { filters, handleChange, handleSearch, filtersUpdated } =
        useFilterState({ baseUrl, params, saveSearchInHistory: false });
    const [showDirectChildren, setShowDirectChildren] = useState<boolean>(
        filters[`${OU_CHILDREN_PREFIX}OnlyDirectChildren`] === 'true' ||
            filters[`${OU_CHILDREN_PREFIX}OnlyDirectChildren`] === undefined,
    );
    const handleShowDirectChildren = useCallback(
        (key, value) => {
            // converting true to undefined to be able to compute `filtersUpdated` correctly
            const valueForParam = value === false ? value : undefined;
            handleChange(key, valueForParam);
            setShowDirectChildren(value);
        },
        [handleChange],
    );
    const { data: orgUnitTypeOptions, isLoading: isLoadingTypes } =
        useGetOrgUnitTypesDropdownOptions();
    const locationOptions = useLocationOptions();
    const instancesOptions = useInstancesOptions();
    const { data: validationStatusOptions, isFetching: isLoadingStatuses } =
        useGetOrgUnitValidationStatus(true);

    return (
        <Grid container spacing={2}>
            <Grid item xs={12} md={3}>
                <InputComponent
                    type="search"
                    keyValue={`${OU_CHILDREN_PREFIX}Search`}
                    value={filters[`${OU_CHILDREN_PREFIX}Search`]}
                    onChange={handleChange}
                    onEnterPressed={handleSearch}
                    label={MESSAGES.textSearch}
                />
                <InputComponent
                    type="select"
                    keyValue={`${OU_CHILDREN_PREFIX}OrgUnitTypeId`}
                    value={filters[`${OU_CHILDREN_PREFIX}OrgUnitTypeId`]}
                    onChange={handleChange}
                    multi
                    options={orgUnitTypeOptions}
                    loading={isLoadingTypes}
                    label={MESSAGES.org_unit_type_id}
                />
                <InputComponent
                    type="checkbox"
                    keyValue={`${OU_CHILDREN_PREFIX}OnlyDirectChildren`}
                    value={showDirectChildren}
                    onChange={handleShowDirectChildren}
                    label={MESSAGES.onlyDirectChildren}
                />
            </Grid>
            <Grid item xs={12} md={3}>
                <InputComponent
                    type="select"
                    keyValue={`${OU_CHILDREN_PREFIX}WithLocation`}
                    value={filters[`${OU_CHILDREN_PREFIX}WithLocation`]}
                    onChange={handleChange}
                    options={locationOptions}
                    label={MESSAGES.location}
                />
                <InputComponent
                    type="select"
                    keyValue={`${OU_CHILDREN_PREFIX}WithShape`}
                    value={filters[`${OU_CHILDREN_PREFIX}WithShape`]}
                    onChange={handleChange}
                    options={locationOptions}
                    label={MESSAGES.shape}
                />
            </Grid>
            <Grid item xs={12} md={3}>
                <InputComponent
                    type="select"
                    keyValue={`${OU_CHILDREN_PREFIX}Group`}
                    value={filters[`${OU_CHILDREN_PREFIX}Group`]}
                    onChange={handleChange}
                    multi
                    options={groups}
                    label={MESSAGES.group}
                />

                <InputComponent
                    type="select"
                    keyValue={`${OU_CHILDREN_PREFIX}HasInstances`}
                    value={filters[`${OU_CHILDREN_PREFIX}HasInstances`]}
                    onChange={handleChange}
                    options={instancesOptions}
                    label={MESSAGES.hasInstances}
                />
                <InputComponent
                    type="select"
                    keyValue={`${OU_CHILDREN_PREFIX}Validation_status`}
                    value={filters[`${OU_CHILDREN_PREFIX}Validation_status`]}
                    onChange={handleChange}
                    options={validationStatusOptions}
                    loading={isLoadingStatuses}
                    clearable={false}
                    label={MESSAGES.validationStatus}
                />
            </Grid>
            <Grid container item xs={12} md={3} justifyContent="flex-end">
                <Box mt={2}>
                    <SearchButton
                        onSearch={handleSearch}
                        disabled={!filtersUpdated}
                    />
                </Box>
            </Grid>
        </Grid>
    );
};
