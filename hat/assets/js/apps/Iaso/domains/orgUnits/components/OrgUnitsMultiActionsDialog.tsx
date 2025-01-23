import React, { FunctionComponent, useState } from 'react';

import ReportIcon from '@mui/icons-material/Report';
import {
    Box,
    Button,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    Tooltip,
    Typography,
    useTheme,
} from '@mui/material';
import { makeStyles } from '@mui/styles';
import {
    commonStyles,
    formatThousand,
    useSafeIntl,
} from 'bluesquare-components';
// @ts-ignore
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { UseMutateAsyncFunction } from 'react-query';
import { useCurrentUser } from '../../../utils/usersUtils';

import ConfirmDialog from '../../../components/dialogs/ConfirmDialogComponent';
import InputComponent from '../../../components/forms/InputComponent';
import { useGetValidationStatus } from '../../forms/hooks/useGetValidationStatus';
import { useGetGroupDropdown } from '../hooks/requests/useGetGroups';
import MESSAGES from '../messages';
import { useGetOrgUnitTypesDropdownOptions } from '../orgUnitTypes/hooks/useGetOrgUnitTypesDropdownOptions';
import { OrgUnit, OrgUnitParams } from '../types/orgUnit';
import { OrgunitType } from '../types/orgunitTypes';
import { SaveData } from '../types/saveMulti';
import { Selection } from '../types/selection';
import { decodeSearch } from '../utils';

type Props = {
    open: boolean;
    params: OrgUnitParams;
    closeDialog: () => void;
    selection: Selection<OrgUnit>;
    saveMulti: UseMutateAsyncFunction<unknown, unknown, unknown, unknown>;
};

const useStyles = makeStyles(theme => ({
    ...commonStyles(theme),
    paper: {
        overflow: 'visible',
    },
    title: {
        paddingBottom: 0,
    },
    content: {
        overflow: 'visible',
        paddingBottom: theme.spacing(2),
    },
    action: {
        paddingBottom: theme.spacing(2),
        paddingRight: theme.spacing(2),
    },
    warningTitle: {
        display: 'flex',
        alignItems: 'center',
    },
    warningIcon: {
        display: 'inline-block',
        marginLeft: theme.spacing(1),
        marginRight: theme.spacing(1),
    },
    warningMessage: {
        display: 'flex',
        justifyContent: 'center',
    },
}));

const stringOfIdsToArrayofIds = stringValue =>
    !stringValue || stringValue === ''
        ? []
        : stringValue.split(',').map(s => parseInt(s, 10));

export const OrgUnitsMultiActionsDialog: FunctionComponent<Props> = ({
    open,
    closeDialog,
    selection: { selectCount, selectedItems, unSelectedItems, selectAll },
    params,
    saveMulti,
}) => {
    const { formatMessage } = useSafeIntl();
    const classes: Record<string, string> = useStyles();
    const theme = useTheme();
    const { data: orgUnitTypes } = useGetOrgUnitTypesDropdownOptions(
        undefined,
        true,
    );
    const [editGroups, setEditGroups] = useState<boolean>(false);
    const [groupsAdded, setGroupsAdded] = useState<number[]>([]);
    const [groupsRemoved, setGroupsRemoved] = useState<number[]>([]);
    const [editOrgUnitType, setEditOrgUnitType] = useState<boolean>(false);
    const [orgUnitType, setOrgUnitType] = useState<OrgunitType | undefined>(
        undefined,
    );
    const [editValidation, setEditValidation] = useState<boolean>(false);
    const [updateGPS, setUpdateGPS] = useState<boolean>(false);
    const [validationStatus, setValidationStatus] = useState<
        string | undefined
    >(undefined);

    const currentUser = useCurrentUser();
    const { data: groups = [], isFetching: isFetchingGroups } =
        useGetGroupDropdown({
            dataSourceId:
                currentUser?.account?.default_version?.data_source?.id,
            sourceVersionId: currentUser?.account?.default_version?.id,
        });
    const isSaveDisabled = () =>
        ((editGroups &&
            groupsAdded.length === 0 &&
            groupsRemoved.length === 0) ||
            (editOrgUnitType && !orgUnitType) ||
            (editValidation && validationStatus === null) ||
            (!editGroups && !editOrgUnitType && !editValidation)) &&
        updateGPS === false;

    const groupsWithoutAdded = [...groups].filter(
        g => groupsAdded.indexOf(g.value) === -1,
    );

    const {
        data: validationStatusOptions,
        isLoading: isLoadingValidationStatusOptions,
    } = useGetValidationStatus();
    const handleSetEditGroups = editEnabled => {
        if (!editEnabled) {
            setGroupsAdded([]);
            setGroupsRemoved([]);
        }
        setEditGroups(editEnabled);
    };
    const handleSetEditOuType = editEnabled => {
        if (!editEnabled) {
            setEditOrgUnitType(false);
        }
        setEditOrgUnitType(editEnabled);
    };
    const handleSetEditValidation = editEnabled => {
        if (!editEnabled) {
            setValidationStatus(undefined);
        }
        setEditValidation(editEnabled);
    };
    const handleSetUpdateGPS = editEnabled => {
        if (!editEnabled) {
            setUpdateGPS(false);
        }
        setUpdateGPS(editEnabled);
    };
    const closeAndReset = () => {
        setEditGroups(false);
        setGroupsAdded([]);
        setGroupsRemoved([]);
        setEditOrgUnitType(false);
        setOrgUnitType(undefined);
        setEditValidation(false);
        setUpdateGPS(false);
        setValidationStatus(undefined);
        closeDialog();
    };
    const saveAndReset = () => {
        const data: SaveData = {};
        if (editGroups) {
            if (groupsAdded.length > 0) {
                data.groups_added = groupsAdded;
            }
            if (groupsRemoved.length > 0) {
                data.groups_removed = groupsRemoved;
            }
        }
        if (editOrgUnitType) {
            data.org_unit_type = orgUnitType;
        }
        if (editValidation) {
            data.validation_status = validationStatus;
        }
        if (!selectAll) {
            data.selected_ids = selectedItems.map(i => i.id);
        } else {
            data.select_all = true;
            data.unselected_ids = unSelectedItems.map(i => i.id);
            // TODO : taken from OrgUnitsFiltersComponent to match
            // their fix but not a fan we should change it
            // when we refactor the search, probably set orgUnitParentId
            // directly in the onchange of OrgUnitTreeviewModal.
            const searches = decodeSearch(params.searches);
            searches.forEach((s, i) => {
                searches[i].orgUnitParentId = searches[i].levels;
            });
            data.searches = searches;
        }
        saveMulti({
            ...data,
            saveGPS: updateGPS,
            saveOtherField: editValidation || editOrgUnitType || editGroups,
        }).then(() => closeAndReset());
    };
    return (
        <Dialog
            fullWidth
            maxWidth="xs"
            open={open}
            classes={{
                paper: classes.paper,
            }}
            onClose={(_event, reason) => {
                if (reason === 'backdropClick') {
                    closeAndReset();
                }
            }}
            scroll="body"
        >
            <DialogTitle className={classes.title}>
                {formatMessage(MESSAGES.multiEditTitle)}
                {` (${formatThousand(selectCount)} `}
                {selectCount === 1 && formatMessage(MESSAGES.titleSingle)}
                {selectCount > 1 && formatMessage(MESSAGES.titleMulti)})
            </DialogTitle>
            <DialogContent className={classes.content}>
                <div>
                    <InputComponent
                        keyValue="editGroups"
                        onChange={(_key, checked) =>
                            handleSetEditGroups(checked)
                        }
                        value={editGroups}
                        type="checkbox"
                        label={MESSAGES.editGroups}
                    />
                    {editGroups && (
                        <>
                            <InputComponent
                                multi
                                clearable
                                keyValue="addGroups"
                                onChange={(_key, value) =>
                                    setGroupsAdded(
                                        stringOfIdsToArrayofIds(value),
                                    )
                                }
                                value={
                                    groupsAdded.length > 0 ? groupsAdded : null
                                }
                                type="select"
                                loading={isFetchingGroups}
                                options={groups}
                                label={MESSAGES.addToGroups}
                            />
                            <InputComponent
                                multi
                                clearable
                                keyValue="removeGroups"
                                onChange={(_key, value) =>
                                    setGroupsRemoved(
                                        stringOfIdsToArrayofIds(value),
                                    )
                                }
                                value={
                                    groupsRemoved.length > 0
                                        ? groupsRemoved
                                        : null
                                }
                                type="select"
                                options={groupsWithoutAdded}
                                label={MESSAGES.removeFromGroups}
                            />
                        </>
                    )}
                </div>
                <div>
                    <InputComponent
                        keyValue="editOrgUnitType"
                        onChange={(_key, checked) =>
                            handleSetEditOuType(checked)
                        }
                        value={editOrgUnitType}
                        type="checkbox"
                        label={MESSAGES.editOrgUnitType}
                    />
                    {editOrgUnitType && (
                        <InputComponent
                            multi={false}
                            clearable
                            keyValue="changeOrgUnitType"
                            onChange={(_key, value) => setOrgUnitType(value)}
                            value={orgUnitType}
                            type="select"
                            options={orgUnitTypes || []}
                            label={MESSAGES.org_unit_type}
                        />
                    )}
                </div>
                <div>
                    <InputComponent
                        keyValue="editValidation"
                        onChange={(_key, checked) =>
                            handleSetEditValidation(checked)
                        }
                        value={editValidation}
                        type="checkbox"
                        label={MESSAGES.editValidation}
                    />
                    {editValidation && (
                        <div className={classes.marginLeft}>
                            <InputComponent
                                keyValue="isValid"
                                onChange={(_key, value) => {
                                    setValidationStatus(value);
                                }}
                                value={validationStatus}
                                type="radio"
                                options={validationStatusOptions || []}
                                loading={isLoadingValidationStatusOptions}
                                labelString=""
                            />
                        </div>
                    )}
                </div>
                <Box style={{ display: 'flex' }}>
                    <InputComponent
                        keyValue="updateGPS"
                        onChange={(_key, checked) =>
                            handleSetUpdateGPS(checked)
                        }
                        value={updateGPS}
                        type="checkbox"
                        label={MESSAGES.useGPSFromSubmission}
                    />
                    <Box position="relative">
                        <Box
                            position="absolute"
                            top={theme.spacing(3)}
                            left={theme.spacing(-1)}
                        >
                            <Tooltip
                                arrow
                                title={formatMessage(MESSAGES.GPSWarning)}
                            >
                                <InfoOutlinedIcon />
                            </Tooltip>
                        </Box>
                    </Box>
                </Box>
            </DialogContent>
            <DialogActions className={classes.action}>
                <Button onClick={closeAndReset} color="primary">
                    {formatMessage(MESSAGES.cancel)}
                </Button>

                <ConfirmDialog
                    withDivider
                    btnMessage={formatMessage(MESSAGES.validate)}
                    question={
                        <Box className={classes.warningTitle}>
                            <ReportIcon
                                className={classes.warningIcon}
                                color="error"
                                fontSize="large"
                            />
                            {formatMessage(MESSAGES.confirmMultiChange)}
                            <ReportIcon
                                className={classes.warningIcon}
                                color="error"
                                fontSize="large"
                            />
                        </Box>
                    }
                    message={
                        <Typography
                            variant="body2"
                            color="error"
                            component="span"
                            className={classes.warningMessage}
                        >
                            {formatMessage(MESSAGES.bulkChangeCount, {
                                count: `${formatThousand(selectCount)}`,
                            })}
                        </Typography>
                    }
                    confirm={() => saveAndReset()}
                    btnDisabled={isSaveDisabled()}
                    btnVariant="text"
                />
            </DialogActions>
        </Dialog>
    );
};
