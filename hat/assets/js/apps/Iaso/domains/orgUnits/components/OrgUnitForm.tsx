/* eslint-disable react/function-component-definition */
import { Box, Grid } from '@mui/material';
import { makeStyles } from '@mui/styles';
import classnames from 'classnames';
import mapValues from 'lodash/mapValues';
import React, {
    FunctionComponent,
    useCallback,
    useEffect,
    useMemo,
    useState,
} from 'react';

import { commonStyles } from 'bluesquare-components';
import { isEqual } from 'lodash';
import { getValues, useFormState } from '../../../hooks/form';
import { DropdownOptions } from '../../../types/utils';
import { OrgUnit, OrgunitInititialState } from '../types/orgUnit';
import { OrgunitType } from '../types/orgunitTypes';
import { OrgUnitInfos } from './OrgUnitInfos';

const initialFormState = (orgUnit: OrgUnit): OrgunitInititialState => ({
    id: orgUnit.id,
    name: orgUnit.name,
    org_unit_type_id: orgUnit.org_unit_type_id
        ? `${orgUnit.org_unit_type_id}`
        : undefined,
    groups: orgUnit.groups?.map(g => g.id) ?? [],
    sub_source: orgUnit.sub_source,
    validation_status: orgUnit.validation_status,
    aliases: orgUnit.aliases ?? ([] as string[]),
    source_id: orgUnit.source_id,
    parent: orgUnit.parent,
    source_ref: orgUnit.source_ref,
    reference_instance_id: orgUnit.reference_instance_id,
    opening_date: orgUnit.opening_date ? orgUnit.opening_date : undefined,
    closed_date: orgUnit.closed_date ? orgUnit.closed_date : undefined,
});

const useStyles = makeStyles(theme => ({
    ...commonStyles(theme),
}));

type Props = {
    orgUnit: OrgUnit;
    orgUnitTypes: OrgunitType[];
    groups: DropdownOptions<string>[];
    saveOrgUnit: (
        newOu: OrgUnit,
        onSuccess: (unit: OrgUnit) => void,
        onError: (error: any) => void,
    ) => void;
    params: Record<string, string>;
    onResetOrgUnit: () => void;
    isFetchingOrgUnitTypes: boolean;
    isFetchingGroups: boolean;
};

export const OrgUnitForm: FunctionComponent<Props> = ({
    orgUnit,
    orgUnitTypes,
    groups,
    saveOrgUnit,
    params,
    onResetOrgUnit,
    isFetchingOrgUnitTypes,
    isFetchingGroups,
}) => {
    const classes: Record<string, string> = useStyles();
    // Making initialState accessible so we can check if the form values have changed and disable save button accordingly
    const initialState = useMemo(() => initialFormState(orgUnit), [orgUnit]);

    const [formState, setFieldValue, setFieldErrors, setFormState] =
        useFormState(initialState);

    // FormState values as dict. Used to enable comparison with initialState
    const currentStateValues: OrgunitInititialState = useMemo(
        () => getValues(formState) as OrgunitInititialState,
        [formState],
    );
    const [orgUnitModified, setOrgUnitModified] = useState(false);
    const handleSave = () => {
        const newOrgUnit = mapValues(formState, v =>
            Object.prototype.hasOwnProperty.call(v, 'value') ? v.value : v,
        );
        newOrgUnit.parent_id = newOrgUnit.parent?.id;
        saveOrgUnit(
            newOrgUnit as OrgUnit,
            savedOrgUnit => {
                setOrgUnitModified(false);
                setFormState(initialFormState(savedOrgUnit));
            },
            error => {
                if (error.status === 400) {
                    error.details.forEach(entry => {
                        setFieldErrors(entry.errorKey, [entry.errorMessage]);
                    });
                }
            },
        );
    };

    const handleChangeField = useCallback(
        (key, value) => {
            const modifiedState: OrgunitInititialState = {
                ...currentStateValues,
                [key]: value,
            };
            const invalidAliases = modifiedState.aliases.includes('');
            if (isEqual(modifiedState, initialState) || invalidAliases) {
                setOrgUnitModified(false);
            } else {
                setOrgUnitModified(true);
            }
            setFieldValue(key, value);
        },
        [setFieldValue, initialState, currentStateValues],
    );

    // TODO change component in blsq-comp library to avoid separate handler
    // This fix assumes we can only add one alias at a time
    const handleChangeAlias = useCallback(
        (key, value) => {
            const orgUnitAliases = orgUnit.aliases ?? [];
            const newAlias = value[value.length - 1];
            const actualAliases = value.filter(alias => alias !== '');
            const modifiedState = { ...currentStateValues, [key]: value };
            if (newAlias !== '' && !isEqual(actualAliases, orgUnitAliases)) {
                setOrgUnitModified(true);
            } else if (
                isEqual(modifiedState, initialState) ||
                newAlias === ''
            ) {
                setOrgUnitModified(false);
            } else if (
                value.length === 0 &&
                !isEqual(modifiedState, initialState)
            ) {
                setOrgUnitModified(true);
            }
            setFieldValue(key, value);
        },
        [orgUnit.aliases, setFieldValue, initialState, currentStateValues],
    );

    const handleChangeInfo = useCallback(
        (key, value) => {
            if (key === 'aliases') {
                handleChangeAlias(key, value);
            } else {
                handleChangeField(key, value);
            }
        },
        [handleChangeAlias, handleChangeField],
    );

    const handleReset = () => {
        setOrgUnitModified(false);
        setFormState(initialFormState(orgUnit));
        onResetOrgUnit();
    };

    const isNewOrgunit = params.orgUnitId === '0';

    useEffect(() => {
        if (orgUnit.id !== formState.id.value) {
            setFormState(initialFormState(orgUnit));
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [orgUnit.id]);
    return (
        <Box pt={isNewOrgunit ? 2 : 0}>
            <Grid
                container
                spacing={0}
                alignItems="center"
                className={classnames(!isNewOrgunit && classes.marginTopBig)}
            >
                <OrgUnitInfos
                    params={params}
                    orgUnitState={formState}
                    orgUnit={orgUnit}
                    orgUnitTypes={orgUnitTypes}
                    groups={groups}
                    onChangeInfo={handleChangeInfo}
                    resetTrigger={!orgUnitModified}
                    handleSave={handleSave}
                    handleReset={handleReset}
                    orgUnitModified={orgUnitModified}
                    isFetchingOrgUnitTypes={isFetchingOrgUnitTypes}
                    isFetchingGroups={isFetchingGroups}
                    referenceInstances={orgUnit.reference_instances}
                />
            </Grid>
        </Box>
    );
};
