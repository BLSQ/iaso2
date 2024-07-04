/* eslint-disable react/no-array-index-key */
import React, { useState, useCallback, useMemo, useEffect } from 'react';
import {
    useSafeIntl,
    commonStyles,
    useSkipEffectOnMount,
    useRedirectToReplace,
} from 'bluesquare-components';
import { Grid, Box, Paper } from '@mui/material';
import { makeStyles } from '@mui/styles';
import TopBar from 'Iaso/components/nav/TopBarComponent';
import { useLocation } from 'react-router-dom';
import { DisplayIfUserHasPerm } from '../../../../../../../hat/assets/js/apps/Iaso/components/DisplayIfUserHasPerm.tsx';
import { useParamsObject } from '../../../../../../../hat/assets/js/apps/Iaso/routing/hooks/useParamsObject.tsx';
import { DistrictsNotFound } from '../shared/DistrictsNotFound.tsx';
import { Filters } from '../shared/Filters.tsx';
import { GraphTitle } from '../shared/GraphTitle.tsx';
import { LqasImHorizontalChart } from '../shared/LqasImHorizontalChart.tsx';
import { DatesIgnored } from '../shared/DatesIgnored.tsx';
import { HorizontalDivider } from '../../../components/HorizontalDivider.tsx';
import { LqasImVerticalChart } from '../shared/LqasImVerticalChart.tsx';
import { Sides } from '../../../constants/types.ts';
import { ImOverviewContainer } from './CountryOverview/ImOverviewContainer.tsx';
import { useImData } from './hooks/useImData.ts';
import MESSAGES from '../../../constants/messages.ts';
import { BadRoundNumbers } from '../shared/BadRoundNumber.tsx';
import { commaSeparatedIdsToArray } from '../../../../../../../hat/assets/js/apps/Iaso/utils/forms';
import { defaultRounds, paperElevation, LIST } from '../shared/constants.ts';
import { baseUrls } from '../../../constants/urls.ts';

const styles = theme => ({
    ...commonStyles(theme),
    filter: { paddingTop: theme.spacing(4), paddingBottom: theme.spacing(4) },
});

const useStyles = makeStyles(styles);

const useImType = () => {
    const { pathname } = useLocation();
    if (pathname.includes(baseUrls.imGlobal)) {
        return { url: baseUrls.imGlobal, type: 'imGlobal' };
    }
    if (pathname.includes(baseUrls.imIhh)) {
        return { url: baseUrls.imIhh, type: 'imIHH' };
    }
    if (pathname.includes(baseUrls.imOhh)) {
        return { url: baseUrls.imOhh, type: 'imOHH' };
    }
    throw new Error(`Invalid pathname: ${pathname}`);
};

export const ImStats = () => {
    const { url: baseUrl, type: imType } = useImType();
    const params = useParamsObject(baseUrl);
    const { campaign, country, rounds } = params;
    const { formatMessage } = useSafeIntl();
    const classes = useStyles();
    const redirectToReplace = useRedirectToReplace();
    const [selectedRounds, setSelectedRounds] = useState(
        rounds ? commaSeparatedIdsToArray(rounds) : defaultRounds,
    );
    const {
        imData,
        isFetching,
        convertedData,
        campaigns,
        campaignsFetching,
        debugData,
        hasScope,
        chartData,
    } = useImData(campaign, country, imType, selectedRounds);

    const dropDownOptions = useMemo(() => {
        return campaigns
            ?.filter(c => c.obr_name === campaign)[0]
            ?.rounds.sort((a, b) => a.number - b.number)
            .map(r => {
                return {
                    label: `Round ${r.number}`,
                    value: r.number,
                };
            });
    }, [campaign, campaigns]);

    const onRoundChange = useCallback(
        index => value => {
            const updatedSelection = [...selectedRounds];
            updatedSelection[index] = value;
            setSelectedRounds(updatedSelection);
            redirectToReplace(baseUrl, {
                ...params,
                rounds: updatedSelection.join(','),
            });
        },
        [baseUrl, params, redirectToReplace, selectedRounds],
    );

    const divider = (
        <HorizontalDivider mt={6} mb={4} ml={-4} mr={-4} displayTrigger />
    );
    useSkipEffectOnMount(() => {
        setSelectedRounds([undefined, undefined]);
    }, [country]);

    useEffect(() => {
        if (dropDownOptions && !rounds) {
            if (dropDownOptions.length === 1) {
                setSelectedRounds([
                    dropDownOptions[0].value,
                    dropDownOptions[0].value,
                ]);
                redirectToReplace(baseUrl, {
                    ...params,
                    rounds: `${dropDownOptions[0].value},${dropDownOptions[0].value}`,
                    rightTab: LIST,
                });
            }
            if (dropDownOptions.length > 1) {
                setSelectedRounds([
                    dropDownOptions[0].value,
                    dropDownOptions[1].value,
                ]);
            }
        }
    }, [dropDownOptions, campaign, rounds, redirectToReplace, params, baseUrl]);

    return (
        <>
            <TopBar
                title={formatMessage(MESSAGES[imType])}
                displayBackButton={false}
            />
            <Box className={classes.containerFullHeightNoTabPadded}>
                <Filters
                    isFetching={isFetching}
                    campaigns={campaigns}
                    campaignsFetching={campaignsFetching}
                    imType={imType}
                    params={params}
                />
                <Grid container spacing={2} direction="row">
                    <Grid
                        item
                        xs={6}
                        key={`IM-map-round round_${selectedRounds[0]}_${0}`}
                    >
                        <ImOverviewContainer
                            round={parseInt(selectedRounds[0], 10)}
                            campaign={campaign}
                            campaigns={campaigns}
                            country={country}
                            data={convertedData}
                            isFetching={isFetching || campaignsFetching}
                            debugData={debugData}
                            paperElevation={paperElevation}
                            type={imType}
                            params={params}
                            onRoundChange={onRoundChange(0)}
                            side={Sides.left}
                            options={dropDownOptions}
                        />
                    </Grid>
                    <Grid
                        item
                        xs={6}
                        key={`IM-map-round round_${selectedRounds[1]}_${1}`}
                    >
                        <ImOverviewContainer
                            round={parseInt(selectedRounds[1], 10)}
                            campaign={campaign}
                            campaigns={campaigns}
                            country={country}
                            data={convertedData}
                            isFetching={isFetching || campaignsFetching}
                            debugData={debugData}
                            paperElevation={paperElevation}
                            type={imType}
                            params={params}
                            side={Sides.right}
                            onRoundChange={onRoundChange(1)}
                            options={dropDownOptions}
                        />
                    </Grid>
                </Grid>
                {campaign && !isFetching && (
                    <>
                        {divider}
                        <Grid container spacing={2} direction="row">
                            <Grid item xs={12}>
                                <GraphTitle
                                    text={formatMessage(MESSAGES.imPerRegion)}
                                    displayTrigger={campaign}
                                />
                            </Grid>
                            {selectedRounds.map((rnd, index) => (
                                <Grid
                                    item
                                    xs={6}
                                    key={`IM-bar-chart ${rnd}_${index}`}
                                >
                                    <Paper elevation={paperElevation}>
                                        <LqasImHorizontalChart
                                            type={imType}
                                            round={parseInt(rnd, 10)}
                                            campaign={campaign}
                                            countryId={parseInt(country, 10)}
                                            data={convertedData}
                                            isLoading={isFetching}
                                        />
                                    </Paper>
                                </Grid>
                            ))}
                        </Grid>
                        {imType === 'imIHH' && (
                            <>
                                {divider}
                                <Grid container spacing={2} direction="row">
                                    <Grid item xs={12}>
                                        <GraphTitle
                                            text={formatMessage(
                                                MESSAGES.reasonsNoFingerMarked,
                                            )}
                                            displayTrigger={
                                                campaign && hasScope
                                            }
                                        />
                                    </Grid>
                                    {chartData.nfm.map(d => (
                                        <Grid item xs={6} key={d.chartKey}>
                                            <Paper elevation={paperElevation}>
                                                <Box p={2}>
                                                    <LqasImVerticalChart
                                                        data={d.data}
                                                        chartKey={d.chartKey}
                                                        title={d.title}
                                                        isLoading={isFetching}
                                                        showChart={Boolean(
                                                            campaign,
                                                        )}
                                                    />
                                                </Box>
                                            </Paper>
                                        </Grid>
                                    ))}
                                </Grid>
                                <HorizontalDivider
                                    mt={6}
                                    mb={4}
                                    ml={0}
                                    mr={0}
                                    displayTrigger
                                />
                                <Grid container spacing={2} direction="row">
                                    <Grid item xs={12}>
                                        <GraphTitle
                                            text={formatMessage(
                                                MESSAGES.reasonsForAbsence,
                                            )}
                                            displayTrigger={
                                                campaign && hasScope
                                            }
                                        />
                                    </Grid>
                                    {chartData.rfa.map(d => (
                                        <Grid item xs={6} key={d.chartKey}>
                                            <Paper elevation={paperElevation}>
                                                <Box p={2}>
                                                    <LqasImVerticalChart
                                                        data={d.data}
                                                        chartKey={d.chartKey}
                                                        title={d.title}
                                                        isLoading={isFetching}
                                                        showChart={Boolean(
                                                            campaign,
                                                        )}
                                                    />
                                                </Box>
                                            </Paper>
                                        </Grid>
                                    ))}
                                </Grid>
                            </>
                        )}
                        {Object.keys(convertedData).length > 0 && (
                            <DisplayIfUserHasPerm permission="iaso_polio_config">
                                <HorizontalDivider
                                    mt={6}
                                    mb={4}
                                    ml={-4}
                                    mr={-4}
                                    displayTrigger
                                />
                                <Grid container item>
                                    <Grid item xs={4}>
                                        <DistrictsNotFound
                                            campaign={campaign}
                                            data={imData.stats}
                                        />
                                    </Grid>
                                    <Grid item xs={4}>
                                        <DatesIgnored
                                            campaign={campaign}
                                            data={imData}
                                        />
                                    </Grid>
                                    <Grid item xs={4}>
                                        <BadRoundNumbers
                                            formsWithBadRoundNumber={
                                                imData?.stats[campaign]
                                                    ?.bad_round_number ?? 0
                                            }
                                        />
                                    </Grid>
                                </Grid>
                            </DisplayIfUserHasPerm>
                        )}
                    </>
                )}
            </Box>
        </>
    );
};
