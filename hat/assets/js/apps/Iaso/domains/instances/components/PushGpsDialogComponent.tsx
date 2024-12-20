import React, { FunctionComponent, useState } from 'react';
import { Grid, Typography } from '@mui/material';
import { useSafeIntl } from 'bluesquare-components';
import ConfirmCancelDialogComponent from '../../../components/dialogs/ConfirmCancelDialogComponent';
import MESSAGES from '../messages';
import { Instance } from '../types/instance';
import { Selection } from '../../orgUnits/types/selection';
import { useGetCheckBulkGpsPush } from '../hooks/useGetCheckBulkGpsPush';
import PushBulkGpsWarning from './PushBulkGpsWarning';

type Props = {
    renderTrigger: (openDialog: boolean) => void;
    selection: Selection<Instance>;
};

const PushGpsDialogComponent: FunctionComponent<Props> = ({
    renderTrigger,
    selection,
}) => {
    const [approveOrgUnitHasGps, setApproveOrgUnitHasGps] =
        useState<boolean>(false);
    const [approveSubmissionNoHasGps, setApproveSubmissionNoHasGps] =
        useState<boolean>(false);
    const onConfirm = closeDialog => {
        return null;
    };

    const { data: checkBulkGpsPush, isError } = useGetCheckBulkGpsPush({
        selected_ids: selection.selectedItems.map(item => item.id).join(','),
        select_all: selection.selectAll,
        unselected_ids: selection.unSelectedItems
            .map(item => item.id)
            .join(','),
    });

    const onClosed = () => {
        return null;
    };

    const onApprove = type => {
        if (type === 'instanceNoGps') {
            if (approveSubmissionNoHasGps) {
                setApproveSubmissionNoHasGps(false);
            } else {
                setApproveSubmissionNoHasGps(true);
            }
        }

        if (type === 'orgUnitHasGps') {
            if (approveOrgUnitHasGps) {
                setApproveOrgUnitHasGps(false);
            } else {
                setApproveOrgUnitHasGps(true);
            }
        }
    };
    let title = MESSAGES.export;
    if (selection) {
        title = {
            ...MESSAGES.pushGpsToOrgUnits,
        };
    }
    const { formatMessage } = useSafeIntl();
    return (
        // @ts-ignore
        <ConfirmCancelDialogComponent
            renderTrigger={({ openDialog }) => renderTrigger(openDialog)}
            titleMessage={title}
            onConfirm={onConfirm}
            confirmMessage={MESSAGES.launch}
            onClosed={onClosed}
            cancelMessage={MESSAGES.cancel}
            maxWidth="sm"
            additionalButton
            additionalMessage={MESSAGES.goToCurrentTask}
            onAdditionalButtonClick={onConfirm}
            allowConfimAdditionalButton
        >
            <Grid container spacing={4} alignItems="center">
                <Grid item xs={12}>
                    <Typography variant="subtitle1">
                        {isError
                            ? formatMessage(
                                  MESSAGES.multipleInstancesOneOrgUnitWarningMessage,
                              )
                            : formatMessage(MESSAGES.pushGpsWarningMessage, {
                                  submissionCount: selection.selectCount,
                                  orgUnitCount: selection.selectCount,
                              })}
                    </Typography>
                </Grid>
                <PushBulkGpsWarning
                    condition={
                        (checkBulkGpsPush?.warning_no_location?.length ?? 0) >
                            0 && (checkBulkGpsPush?.error_ids?.length ?? 0) <= 0
                    }
                    message={MESSAGES.noGpsForSomeInstaces}
                    linkTo="url"
                    approveCondition={approveSubmissionNoHasGps}
                    onApproveClick={() => onApprove('instanceNoGps')}
                />
                <PushBulkGpsWarning
                    condition={
                        (checkBulkGpsPush?.warning_overwrite?.length ?? 0) >
                            0 && (checkBulkGpsPush?.error_ids?.length ?? 0) <= 0
                    }
                    message={MESSAGES.someOrgUnitsHasAlreadyGps}
                    linkTo="url"
                    approveCondition={approveOrgUnitHasGps}
                    onApproveClick={() => onApprove('orgUnitHasGps')}
                />
            </Grid>
        </ConfirmCancelDialogComponent>
    );
};
export default PushGpsDialogComponent;
