import React, { FunctionComponent } from 'react';

import { Box, Button, Grid } from '@mui/material';

import { makeStyles } from '@mui/styles';

import {
    FormControl as FormControlComponent,
    useSafeIntl,
} from 'bluesquare-components';
import InputComponent from '../../../components/forms/InputComponent';
import { commaSeparatedIdsToArray } from '../../../utils/forms';
import MESSAGES from '../messages';
import { OrgUnitTreeviewModal } from './TreeView/OrgUnitTreeviewModal';

import { OrgUnitCreationDetails } from './OrgUnitCreationDetails';

import { DisplayIfUserHasPerm } from '../../../components/DisplayIfUserHasPerm';
import DatesRange from '../../../components/filters/DatesRange';
import { DropdownOptions } from '../../../types/utils';
import { ORG_UNITS } from '../../../utils/permissions';
import { useCheckUserHasWritePermissionOnOrgunit } from '../../../utils/usersUtils';
import { useGetValidationStatus } from '../../forms/hooks/useGetValidationStatus';
import { Instance } from '../../instances/types/instance';
import { OrgUnit, OrgUnitState } from '../types/orgUnit';
import { OrgunitType } from '../types/orgunitTypes';
import { OrgUnitMultiReferenceInstances } from './OrgUnitMultiReferenceInstances';
import { useGetOrgUnit } from './TreeView/requests';

const useStyles = makeStyles(theme => ({
    speedDialTop: {
        top: theme.spacing(12.5),
    },
    marginLeft: {
        marginLeft: `${theme.spacing(2)} !important`,
    },
    divAliasWrapper: {
        position: 'relative',
    },
    divAliasOverlay: {
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        cursor: 'not-allowed',
    },
}));

type Props = {
    orgUnitState: OrgUnitState;
    onChangeInfo: (
        key: string,
        value: string | number | string[] | number[],
    ) => void;
    orgUnitTypes: OrgunitType[];
    groups: DropdownOptions<string>[];
    resetTrigger: boolean;
    params: Record<string, string>;
    handleSave: () => void;
    handleReset: () => void;
    orgUnitModified: boolean;
    isFetchingOrgUnitTypes: boolean;
    isFetchingGroups: boolean;
    referenceInstances: Instance[];
    orgUnit: OrgUnit;
};

export const OrgUnitInfos: FunctionComponent<Props> = ({
    orgUnitState,
    onChangeInfo,
    orgUnitTypes,
    groups,
    resetTrigger,
    params,
    handleSave,
    handleReset,
    orgUnitModified,
    isFetchingOrgUnitTypes,
    isFetchingGroups,
    referenceInstances,
    orgUnit,
}) => {
    const classes = useStyles();
    const { formatMessage } = useSafeIntl();

    const isNewOrgunit = params.orgUnitId === '0';
    const isSaveDisabled =
        orgUnitState.name.value === '' ||
        orgUnitState.org_unit_type_id.value === null ||
        !orgUnitModified;

    const {
        data: validationStatusOptions,
        isLoading: isLoadingValidationStatusOptions,
    } = useGetValidationStatus();
    const { data: parentOrgunit } = useGetOrgUnit(
        orgUnitState.parent.value
            ? `${orgUnitState.parent.value.id}`
            : undefined,
    );
    const hasManagementPermission = useCheckUserHasWritePermissionOnOrgunit(
        orgUnit?.org_unit_type_id,
    );
    const disabled = !hasManagementPermission && !isNewOrgunit;
    return (
        <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
                <InputComponent
                    keyValue="name"
                    type="text"
                    required
                    onChange={onChangeInfo}
                    value={orgUnitState.name.value}
                    errors={orgUnitState.name.errors}
                    label={MESSAGES.name}
                    disabled={disabled}
                />

                <InputComponent
                    keyValue="org_unit_type_id"
                    onChange={onChangeInfo}
                    required
                    value={
                        isFetchingOrgUnitTypes
                            ? undefined
                            : orgUnitState.org_unit_type_id.value
                    }
                    errors={orgUnitState.org_unit_type_id.errors}
                    type="select"
                    loading={isFetchingOrgUnitTypes}
                    options={orgUnitTypes.map(t => ({
                        label: t.name,
                        value: t.id,
                    }))}
                    label={MESSAGES.org_unit_type_id}
                    disabled={disabled}
                />
                <InputComponent
                    keyValue="groups"
                    onChange={(name, value) => {
                        onChangeInfo(name, commaSeparatedIdsToArray(value));
                    }}
                    multi
                    value={
                        isFetchingGroups ? undefined : orgUnitState.groups.value
                    }
                    loading={isFetchingGroups}
                    errors={orgUnitState.groups.errors}
                    type="select"
                    options={groups}
                    label={MESSAGES.groups}
                    disabled={disabled}
                />
                <div className={classes.divAliasWrapper}>
                    <InputComponent
                        keyValue="aliases"
                        onChange={onChangeInfo}
                        value={orgUnitState.aliases.value}
                        type="arrayInput"
                    />
                    {disabled && <div className={classes.divAliasOverlay} />}
                </div>
            </Grid>

            <Grid item xs={12} md={4}>
                <InputComponent
                    keyValue="validation_status"
                    clearable={false}
                    onChange={onChangeInfo}
                    errors={orgUnitState.validation_status.errors}
                    value={orgUnitState.validation_status.value}
                    type="select"
                    label={MESSAGES.status}
                    loading={isLoadingValidationStatusOptions}
                    options={validationStatusOptions || []}
                    disabled={disabled}
                />
                <InputComponent
                    keyValue="source_ref"
                    type="text"
                    value={orgUnitState.source_ref.value || ''}
                    onChange={onChangeInfo}
                    errors={orgUnitState.source_ref.errors}
                    disabled={disabled}
                />

                <FormControlComponent
                    errors={orgUnitState.parent.errors}
                    id="ou-tree-input"
                >
                    <OrgUnitTreeviewModal
                        toggleOnLabelClick={false}
                        titleMessage={MESSAGES.selectParentOrgUnit}
                        onConfirm={treeviewOrgUnit => {
                            if (
                                (treeviewOrgUnit
                                    ? treeviewOrgUnit.id
                                    : null) !== orgUnitState.parent?.value?.id
                            ) {
                                onChangeInfo('parent', treeviewOrgUnit);
                            }
                        }}
                        source={orgUnit.source_id}
                        initialSelection={parentOrgunit}
                        resetTrigger={resetTrigger}
                        disabled={disabled}
                    />
                </FormControlComponent>
                <DatesRange
                    keyDateFrom="opening_date"
                    keyDateTo="closed_date"
                    onChangeDate={onChangeInfo}
                    dateFrom={
                        orgUnitState.opening_date.value as string | undefined
                    }
                    dateTo={
                        orgUnitState.closed_date.value as string | undefined
                    }
                    labelFrom={MESSAGES.openingDate}
                    labelTo={MESSAGES.closingDate}
                    marginTop={0}
                    disabled={disabled}
                />
                <DisplayIfUserHasPerm permissions={[ORG_UNITS]}>
                    <Grid
                        container
                        item
                        xs={12}
                        justifyContent="flex-end"
                        alignItems="center"
                    >
                        <Box mt={1}>
                            {!isNewOrgunit && (
                                <Button
                                    className={classes.marginLeft}
                                    disabled={!orgUnitModified}
                                    variant="contained"
                                    onClick={() => handleReset()}
                                >
                                    {formatMessage(MESSAGES.cancel)}
                                </Button>
                            )}
                            <Button
                                id="save-ou"
                                disabled={isSaveDisabled}
                                variant="contained"
                                className={classes.marginLeft}
                                color="primary"
                                onClick={handleSave}
                            >
                                {formatMessage(MESSAGES.save)}
                            </Button>
                        </Box>
                    </Grid>
                </DisplayIfUserHasPerm>
            </Grid>

            <Grid item xs={12} md={4}>
                <Box mt={2}>
                    <OrgUnitCreationDetails orgUnit={orgUnit} params={params} />
                </Box>
            </Grid>

            {referenceInstances && referenceInstances.length > 0 && (
                <OrgUnitMultiReferenceInstances
                    referenceInstances={referenceInstances}
                />
            )}
        </Grid>
    );
};
