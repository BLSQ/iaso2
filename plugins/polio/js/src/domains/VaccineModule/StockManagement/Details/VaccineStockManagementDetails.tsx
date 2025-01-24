import { Box, Button, Grid, Paper, Tab, Tabs, Typography } from '@mui/material';
import { makeStyles } from '@mui/styles';
import {
    commonStyles,
    textPlaceholder,
    useGoBack,
    useRedirectTo,
    useSafeIntl,
} from 'bluesquare-components';
import React, { FunctionComponent, useCallback } from 'react';
import TopBar from '../../../../../../../../hat/assets/js/apps/Iaso/components/nav/TopBarComponent';
import { useTabs } from '../../../../../../../../hat/assets/js/apps/Iaso/hooks/useTabs';
import { useParamsObject } from '../../../../../../../../hat/assets/js/apps/Iaso/routing/hooks/useParamsObject';
import { baseUrls } from '../../../../constants/urls';
import { EARMARKED, UNUSABLE_VIALS, USABLE_VIALS } from '../constants';
import {
    useGetEarmarked,
    useGetStockManagementSummary,
    useGetUnusableVials,
    useGetUsableVials,
} from '../hooks/api';
import MESSAGES from '../messages';
import { StockManagementDetailsParams, TabValue } from '../types';
import { VaccineStockManagementSummary } from './Summary/VaccineStockManagementSummary';
import {
    VaccineStockManagementDetailsTableUnusable,
    VaccineStockManagementDetailsTableUsable,
} from './Table/VaccineStockManagementDetailsTable';

const useStyles = makeStyles(theme => {
    return {
        ...commonStyles(theme),
        marginTop: {
            marginTop: theme.spacing(2),
        },
        bigMarginTop: {
            marginTop: theme.spacing(4),
        },
    };
});
const baseUrl = baseUrls.stockManagementDetails;
export const VaccineStockManagementDetails: FunctionComponent = () => {
    const params = useParamsObject(
        baseUrl,
    ) as unknown as StockManagementDetailsParams;
    const goBack = useGoBack(baseUrls.stockManagement);
    const redirectTo = useRedirectTo();
    const { formatMessage } = useSafeIntl();
    const classes: Record<string, string> = useStyles();
    const initialTab = (params.tab as TabValue) ?? USABLE_VIALS;
    const { tab, handleChangeTab } = useTabs<TabValue>({
        params,
        defaultTab: initialTab,
        baseUrl,
    });

    // Make 1 API call with both usable and not usable + country and campaign
    const { data: usableVials, isFetching: isFetchingUsable } =
        useGetUsableVials(params, tab === USABLE_VIALS);

    const { data: unusableVials, isFetching: isFetchingUnusable } =
        useGetUnusableVials(params, tab === UNUSABLE_VIALS);

    const { data: earmarked, isFetching: isFetchingEarmarked } =
        useGetEarmarked(params, tab === EARMARKED);

    const { data: summary, isLoading: isLoadingSummary } =
        useGetStockManagementSummary(params.id);

    const goToStockVariation = useCallback(() => {
        redirectTo(baseUrls.stockVariation, {
            ...params,
            id: params.id,
            tab: 'forma',
        });
    }, [params, redirectTo]);

    const isBopv = summary?.vaccine_type === 'bOPV';

    const title = `${formatMessage(MESSAGES.stockDetails)}: ${
        summary?.country_name ?? textPlaceholder
    } - ${summary?.vaccine_type ?? textPlaceholder}`;

    return (
        <>
            <TopBar title={title} displayBackButton goBack={goBack} />

            <Box className={classes.containerFullHeightPadded}>
                <Grid container>
                    <Grid item xs={12} sm={6} md={4}>
                        <VaccineStockManagementSummary
                            isLoading={isLoadingSummary}
                            data={summary}
                        />
                    </Grid>
                    <Grid
                        container
                        item
                        xs={12}
                        sm={6}
                        md={8}
                        justifyContent="flex-end"
                    >
                        <Box>
                            <Button
                                variant="contained"
                                color="primary"
                                onClick={goToStockVariation}
                            >
                                {formatMessage(MESSAGES.stockVariation)}
                            </Button>
                        </Box>
                    </Grid>
                </Grid>
                <Tabs
                    value={tab}
                    classes={{
                        root: classes.bigMarginTop,
                    }}
                    onChange={handleChangeTab}
                >
                    <Tab
                        key={USABLE_VIALS}
                        value={USABLE_VIALS}
                        label={formatMessage(MESSAGES.usable)}
                    />
                    {!isBopv && (
                        <Tab
                            key={UNUSABLE_VIALS}
                            value={UNUSABLE_VIALS}
                            label={formatMessage(MESSAGES.unusable)}
                        />
                    )}
                    <Tab
                        key={EARMARKED}
                        value={EARMARKED}
                        label={formatMessage(MESSAGES.earmarked)}
                    />
                </Tabs>
                <Paper elevation={2} className={classes.marginTop}>
                    <Box pt={2} px={2}>
                        <Typography variant="h5" color="primary">
                            {formatMessage(MESSAGES[tab])}
                        </Typography>

                        {/* Using 2 tables to avoid messing up the Tables internal state, which will create bugs */}
                        {tab === USABLE_VIALS && (
                            <VaccineStockManagementDetailsTableUsable
                                params={params}
                                paramsPrefix={tab}
                                data={usableVials}
                                isFetching={isFetchingUsable}
                            />
                        )}
                        {tab === UNUSABLE_VIALS && (
                            <VaccineStockManagementDetailsTableUnusable
                                params={params}
                                paramsPrefix={tab}
                                data={unusableVials}
                                isFetching={isFetchingUnusable}
                            />
                        )}
                        {tab === EARMARKED && (
                            <VaccineStockManagementDetailsTableUnusable
                                params={params}
                                paramsPrefix={tab}
                                data={earmarked}
                                isFetching={isFetchingEarmarked}
                            />
                        )}
                    </Box>
                </Paper>
            </Box>
        </>
    );
};
