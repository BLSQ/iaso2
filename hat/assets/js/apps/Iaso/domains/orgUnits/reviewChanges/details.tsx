import React, { FunctionComponent, useMemo } from 'react';
import { Box } from '@mui/material';
import {
    IconButton as IconButtonBlsq,
    useGoBack,
    useSafeIntl,
} from 'bluesquare-components';
import TopBar from '../../../components/nav/TopBarComponent';
import { baseUrls } from '../../../constants/urls';
import { useParamsObject } from '../../../routing/hooks/useParamsObject';
import { SxStyles } from '../../../types/general';
import { ApproveOrgUnitChangesButtons } from './Components/ReviewOrgUnitChangesButtons';
import { ReviewOrgUnitChangesTitle } from './Components/ReviewOrgUnitChangesTitle';
import { useGetApprovalProposal } from './hooks/api/useGetApprovalProposal';
import { useSaveChangeRequest } from './hooks/api/useSaveChangeRequest';
import { useNewFields } from './hooks/useNewFields';
import MESSAGES from './messages';
import { ReviewOrgUnitChangesDetailsTable } from './Tables/details/ReviewOrgUnitChangesDetailsTable';
import {
    ChangeRequestValidationStatus,
    OrgUnitChangeRequestDetailParams,
} from './types';

const styles: SxStyles = {
    container: theme => ({
        width: '100%',
        height: `calc(100vh - 65px)`,
        padding: theme.spacing(4),
        margin: 0,
        overflow: 'hidden',
        backgroundColor: 'white',
        [theme.breakpoints.down('md')]: {
            padding: theme.spacing(2),
        },
    }),
    body: theme => ({
        width: '100%',
        maxHeight: `calc(100vh - 200px)`,
        padding: 0,
        margin: 0,
        overflow: 'auto',
        border: `1px solid ${(theme.palette as any).border.main}`,
        borderRadius: 2,
    }),
};

export const ReviewOrgUnitChangesDetail: FunctionComponent = () => {
    const { formatMessage } = useSafeIntl();

    const params = useParamsObject(
        baseUrls.orgUnitsChangeRequestDetail,
    ) as unknown as OrgUnitChangeRequestDetailParams;

    const { data: changeRequest, isFetching: isFetchingChangeRequest } =
        useGetApprovalProposal(Number(params.changeRequestId));
    const isNew: boolean =
        !isFetchingChangeRequest && changeRequest?.status === 'new';
    const isNewOrgUnit = changeRequest
        ? changeRequest.org_unit.validation_status === 'NEW'
        : false;
    const { newFields, setSelected } = useNewFields(changeRequest);
    const goBack = useGoBack(baseUrls.orgUnitsChangeRequest);
    const titleMessage = useMemo(() => {
        if (changeRequest?.status === 'rejected') {
            return formatMessage(MESSAGES.seeRejectedChanges);
        }
        if (changeRequest?.status === 'approved') {
            return formatMessage(MESSAGES.seeApprovedChanges);
        }
        if (isNewOrgUnit) {
            return formatMessage(MESSAGES.validateOrRejectNewOrgUnit);
        }
        return formatMessage(MESSAGES.validateOrRejectChanges);
    }, [changeRequest?.status, formatMessage, isNewOrgUnit]);
    const { mutate: submitChangeRequest, isLoading: isSaving } =
        useSaveChangeRequest(() => goBack(), Number(params.changeRequestId));

    return (
        <Box>
            <TopBar
                title={formatMessage(MESSAGES.reviewChangeProposal, {
                    name: changeRequest?.org_unit.name,
                })}
                goBack={goBack}
                displayBackButton
            />
            <Box sx={styles.container}>
                {!isFetchingChangeRequest && (
                    <ReviewOrgUnitChangesTitle
                        titleMessage={titleMessage}
                        changeRequest={changeRequest}
                        isFetchingChangeRequest={isFetchingChangeRequest}
                    />
                )}
                <Box sx={styles.body}>
                    <ReviewOrgUnitChangesDetailsTable
                        isSaving={isSaving}
                        changeRequest={changeRequest}
                        isFetchingChangeRequest={isFetchingChangeRequest}
                        newFields={newFields}
                        setSelected={setSelected}
                        isNewOrgUnit={isNewOrgUnit}
                    />
                </Box>

                <ApproveOrgUnitChangesButtons
                    newFields={newFields}
                    isNew={isNew}
                    submitChangeRequest={submitChangeRequest}
                    isNewOrgUnit={isNewOrgUnit}
                    changeRequest={changeRequest}
                />
            </Box>
        </Box>
    );
};

type PropsIcon = {
    changeRequestId: number;
    status: ChangeRequestValidationStatus;
};

export const IconButton: FunctionComponent<PropsIcon> = ({
    changeRequestId,
    status,
}) => {
    let message = MESSAGES.validateOrRejectChanges;
    if (status === 'rejected') {
        message = MESSAGES.seeRejectedChanges;
    }
    if (status === 'approved') {
        message = MESSAGES.seeApprovedChanges;
    }
    return (
        <IconButtonBlsq
            url={`/${baseUrls.orgUnitsChangeRequestDetail}/changeRequestId/${changeRequestId}`}
            tooltipMessage={message}
            size="small"
            icon={status === 'new' ? 'edit' : 'remove-red-eye'}
        />
    );
};
