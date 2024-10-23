import { Box } from '@mui/material';
import { useSafeIntl, useRedirectToReplace } from 'bluesquare-components';
import React, { FunctionComponent, useEffect, useMemo, useState } from 'react';
import TopBar from '../../../../../../../hat/assets/js/apps/Iaso/components/nav/TopBarComponent';
import { TableWithDeepLink } from '../../../../../../../hat/assets/js/apps/Iaso/components/tables/TableWithDeepLink';
import MESSAGES from '../../../constants/messages';
import { useStyles } from '../../../styles/theme';
import {
    CampaignsFilters,
    getRedirectUrl,
} from '../../Calendar/campaignCalendar/CampaignsFilters';
import {
    Options as GetCampaignOptions,
    useCampaignParams,
    useGetCampaigns,
    useGetCampaignsAsCsv,
} from '../hooks/api/useGetCampaigns';
import { useRemoveCampaign } from '../hooks/api/useRemoveCampaign';
import { useRestoreCampaign } from '../hooks/api/useRestoreCampaign';
import { DashboardButtons } from './DashboardButtons';
import { useCampaignsTableColumns } from './useCampaignsTableColumns';
import { useParamsObject } from '../../../../../../../hat/assets/js/apps/Iaso/routing/hooks/useParamsObject';
import { baseUrls } from '../../../constants/urls';
import { useActiveParams } from '../../../../../../../hat/assets/js/apps/Iaso/routing/hooks/useActiveParams';

const baseUrl = baseUrls.campaigns;

export const Dashboard: FunctionComponent = () => {
    const params = useParamsObject(baseUrl);
    const { formatMessage } = useSafeIntl();
    const classes: Record<string, string> = useStyles();
    const paramsToUse = useActiveParams(params);
    const apiParams: GetCampaignOptions = useCampaignParams(paramsToUse);
    const [campaignType, setCampaignType] = useState(params.campaignType);
    const [isTypeSet, setIsTypeSet] = useState(!!params.campaignType);
    const { data: rawCampaigns, isFetching } = useGetCampaigns(
        apiParams,
        undefined,
        undefined,
        { keepPreviousData: true },
    );
    const exportToCSV = useGetCampaignsAsCsv(apiParams);

    const campaigns = useMemo(() => {
        if (!rawCampaigns) return rawCampaigns;
        return {
            ...rawCampaigns,
            campaigns: rawCampaigns.campaigns.map(campaign => ({
                ...campaign,
                grouped_campaigns:
                    campaign.grouped_campaigns.length > 0
                        ? campaign.grouped_campaigns
                        : null,
            })),
        };
    }, [rawCampaigns]);

    // Leaving the API code for delete and restore here, so we cxan use isLoading for the table
    const { mutate: removeCampaign, isLoading: isDeleting } =
        useRemoveCampaign();
    const { mutate: restoreCampaign, isLoading: isRestoring } =
        useRestoreCampaign();

    const handleDeleteConfirmDialogConfirm = id => {
        removeCampaign(id);
    };
    const handleRestoreDialogConfirm = id => {
        restoreCampaign(id);
    };

    const columns = useCampaignsTableColumns({
        showOnlyDeleted: Boolean(params.showOnlyDeleted),
        handleClickDeleteRow: handleDeleteConfirmDialogConfirm,
        handleClickRestoreRow: handleRestoreDialogConfirm,
        params,
    });
    const redirectToReplace = useRedirectToReplace();
    const redirectUrl = getRedirectUrl(false, false);
    useEffect(() => {
        if (!params.campaignType && !isTypeSet) {
            setCampaignType('polio');
            setIsTypeSet(true);
            redirectToReplace(redirectUrl, {
                ...params,
                campaignType: 'polio',
            });
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    return (
        <>
            <TopBar
                title={formatMessage(MESSAGES.campaigns)}
                displayBackButton={false}
            />
            <Box className={classes.containerFullHeightNoTabPadded}>
                <CampaignsFilters
                    params={params}
                    setCampaignType={setCampaignType}
                    campaignType={campaignType}
                />
                <Box mb={2}>
                    <DashboardButtons exportToCSV={exportToCSV} />
                </Box>
                <TableWithDeepLink
                    data={campaigns?.campaigns ?? []}
                    count={campaigns?.count}
                    pages={campaigns?.pages}
                    params={apiParams}
                    columns={columns}
                    baseUrl={baseUrl}
                    marginTop={false}
                    extraProps={{
                        loading: isFetching || isDeleting || isRestoring,
                    }}
                />
            </Box>
        </>
    );
};
