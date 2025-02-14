import React, { FunctionComponent, useEffect, useState, useMemo } from 'react';
import { Box, Grid, Theme } from '@mui/material';
import { makeStyles } from '@mui/styles';
import {
    useSafeIntl,
    commonStyles,
    IntlFormatMessage,
    useRedirectToReplace,
    useGoBack,
} from 'bluesquare-components';

import TopBar from '../../../../components/nav/TopBarComponent';
import ErrorPaperComponent from '../../../../components/papers/ErrorPaperComponent';
import { baseUrls } from '../../../../constants/urls';
import { useParamsObject } from '../../../../routing/hooks/useParamsObject';
import {
    useGetInstanceLogs,
    useGetInstanceLogDetail,
} from '../hooks/useGetInstanceLogs';
import MESSAGES from '../messages';
import { InstanceLogDetail } from './InstanceLogDetail';
import { InstanceLogInfos } from './InstanceLogInfos';

type Params = {
    instanceIds: string;
    logA: string;
    logB: string;
};

const useStyles = makeStyles((theme: Theme) => ({
    ...commonStyles(theme),
}));

export const CompareInstanceLogs: FunctionComponent = () => {
    const params = useParamsObject(
        baseUrls.compareInstanceLogs,
    ) as unknown as Params;
    const goBack = useGoBack(baseUrls.instances);
    const redirectToReplace = useRedirectToReplace();
    const { instanceIds: instanceId } = params;

    const {
        data: instanceLogsDropdown,
        isFetching: isFetchingInstanceLogs,
        isError,
    } = useGetInstanceLogs(instanceId);

    const [
        {
            data: instanceLogA,
            isFetching: isInstanceLogAFetching,
            isError: isInstanceLogAError,
        },
        {
            data: instanceLogB,
            isFetching: isInstanceLogBFetching,
            isError: isInstanceLogBError,
        },
    ] = useGetInstanceLogDetail(instanceId, [params.logA, params.logB]);

    const instanceLogContent = useMemo(
        () => ({
            logA: instanceLogA?.new_value[0]?.fields,
            logB: instanceLogB?.new_value[0]?.fields,
            logAFiles: instanceLogA?.files,
            logBFiles: instanceLogB?.files,
            fields: instanceLogA?.possible_fields,
        }),
        [instanceLogA, instanceLogB],
    );
    const isLogDetailLoading = isInstanceLogAFetching || isInstanceLogBFetching;
    const isLogDetailError = isInstanceLogAError || isInstanceLogBError;
    const classes: Record<string, string> = useStyles();

    const { formatMessage }: { formatMessage: IntlFormatMessage } =
        useSafeIntl();

    const [logAInitialValue, setLogAInitialValue] = useState<
        number | undefined
    >(undefined);
    const [logBInitialValue, setLogBInitialValue] = useState<
        number | undefined
    >(undefined);

    const handleChange = (key, value) => {
        const newParams = {
            ...params,
            [key]: value,
        };
        redirectToReplace(baseUrls.compareInstanceLogs, newParams);
    };

    useEffect(() => {
        if (instanceLogsDropdown) {
            const newParams: Params = {
                ...params,
            };
            const logADropDownValue = instanceLogsDropdown?.slice(-1)[0]?.value;
            const logBDropDownValue = instanceLogsDropdown[0]?.value;
            if (!params.logA && logADropDownValue) {
                newParams.logA = logADropDownValue.toString();
            }
            if (!params.logB && logBDropDownValue) {
                newParams.logB = logBDropDownValue.toString();
            }
            if (
                (!params.logA && logADropDownValue) ||
                (!params.logB && logBDropDownValue)
            ) {
                redirectToReplace(baseUrls.compareInstanceLogs, newParams);
            }
        }
    }, [instanceLogsDropdown, params, redirectToReplace]);

    useEffect(() => {
        setLogAInitialValue(
            instanceLogsDropdown && instanceLogsDropdown?.slice(-1)[0]?.value,
        );
        setLogBInitialValue(
            instanceLogsDropdown && instanceLogsDropdown[0]?.value,
        );
    }, [instanceLogsDropdown, isFetchingInstanceLogs]);

    if (isError) {
        return (
            <ErrorPaperComponent message={formatMessage(MESSAGES.errorLog)} />
        );
    }

    return (
        <>
            <TopBar
                title={formatMessage(MESSAGES.instanceLogsTitle)}
                displayBackButton
                goBack={goBack}
            />
            <Box className={classes.containerFullHeightNoTabPadded}>
                <Grid
                    container
                    spacing={3}
                    display="flex"
                    justifyContent="flex-end"
                >
                    <Grid xs={12} md={4.5} item>
                        <InstanceLogInfos
                            log="logA"
                            logTitle="Version A"
                            dropDownHandleChange={handleChange}
                            value={params.logA || logAInitialValue}
                            label={MESSAGES.instanceLogsVersionA}
                            user={instanceLogA?.user}
                            infos={instanceLogContent.logA}
                            loading={isInstanceLogAFetching}
                            options={instanceLogsDropdown?.filter(
                                instance =>
                                    instance.value !==
                                    (parseInt(params.logB, 10) ||
                                        logBInitialValue),
                            )}
                            dropDownLoading={isFetchingInstanceLogs}
                        />
                    </Grid>
                    <Grid xs={12} md={4.5} item>
                        <InstanceLogInfos
                            log="logB"
                            logTitle="Version B"
                            dropDownHandleChange={handleChange}
                            value={params.logB || logBInitialValue}
                            label={MESSAGES.instanceLogsVersionB}
                            options={instanceLogsDropdown?.filter(
                                instance =>
                                    instance.value !==
                                    (parseInt(params.logA, 10) ||
                                        logAInitialValue),
                            )}
                            loading={isFetchingInstanceLogs}
                            user={instanceLogA?.user}
                            infos={instanceLogContent.logB}
                            dropDownLoading={isInstanceLogBFetching}
                        />
                    </Grid>

                    <Grid xs={12} md={12} item>
                        <InstanceLogDetail
                            instanceLogContent={instanceLogContent}
                            isLogDetailLoading={isLogDetailLoading}
                            isLogDetailError={isLogDetailError}
                        />
                    </Grid>
                </Grid>
            </Box>
        </>
    );
};
