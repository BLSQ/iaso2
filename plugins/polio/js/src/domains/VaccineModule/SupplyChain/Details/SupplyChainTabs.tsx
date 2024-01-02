import React, { FunctionComponent } from 'react';
import { commonStyles, useSafeIntl } from 'bluesquare-components';
import { Tab, Tabs } from '@mui/material';
import { makeStyles } from '@mui/styles';
import { TabWithInfoIcon } from '../../../../../../../../hat/assets/js/apps/Iaso/components/nav/TabWithInfoIcon';
import MESSAGES from '../messages';
import { PREALERT, VAR, VRF } from '../constants';
import { TabValue } from '../types';

type Props = {
    tab: TabValue;
    disabled: boolean;
    // eslint-disable-next-line no-unused-vars
    onChangeTab: (_event: any, newTab: TabValue) => void;
};

const useStyles = makeStyles(theme => {
    return {
        ...commonStyles(theme),
    };
});

export const SupplyChainTabs: FunctionComponent<Props> = ({
    tab,
    onChangeTab,
    disabled,
}) => {
    const { formatMessage } = useSafeIntl();
    const classes: Record<string, string> = useStyles();
    return (
        <Tabs
            value={tab}
            classes={{
                root: classes.tabs,
                // indicator: classes.indicator,
            }}
            onChange={onChangeTab}
            // textColor="secondary"
            indicatorColor="secondary"
        >
            <TabWithInfoIcon
                key={VRF}
                value={VRF}
                title={formatMessage(MESSAGES[VRF])}
                disabled={false}
                hasTabError={false}
                handleChange={onChangeTab}
                showIcon={false}
                tooltipMessage=""
            />
            {/* TODO extract Tabs component */}
            <TabWithInfoIcon
                key={PREALERT}
                value={PREALERT}
                title={formatMessage(MESSAGES[PREALERT])}
                // disable if no saved VRF to avoid users trying to save prealert before vrf
                disabled={disabled}
                hasTabError={false}
                handleChange={onChangeTab}
                showIcon={disabled}
                tooltipMessage={formatMessage(MESSAGES.pleaseCreateVrf)}
            />
            <TabWithInfoIcon
                key={VAR}
                value={VAR}
                title={formatMessage(MESSAGES[VAR])}
                // disable if no saved VRF to avoid users trying to save VAR before vrf
                disabled={disabled}
                hasTabError={false}
                handleChange={onChangeTab}
                showIcon={disabled}
                tooltipMessage={formatMessage(MESSAGES.pleaseCreateVrf)}
            />
        </Tabs>
    );
};
