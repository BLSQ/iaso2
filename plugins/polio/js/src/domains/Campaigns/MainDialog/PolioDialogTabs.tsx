import { Tabs } from '@mui/material';
import React, { FunctionComponent } from 'react';
import { useStyles } from '../../../styles/theme';
import { PolioDialogTab } from './PolioDialogTab';

export type Tab = {
    title: string;
    form: FunctionComponent;
    hasTabError: boolean;
    key: string;
    disabled?: boolean;
    disabledMessage?: string;
};

type Props = {
    selectedTab: number;
    handleChange: (_event: any, newValue: number) => void;
    tabs: Tab[];
};

export const PolioDialogTabs: FunctionComponent<Props> = ({
    selectedTab,
    handleChange,
    tabs,
}) => {
    const classes: Record<string, string> = useStyles();

    return (
        <Tabs
            value={selectedTab}
            className={classes.tabs}
            textColor="primary"
            aria-label="disabled tabs example"
            variant="scrollable"
            scrollButtons="auto"
        >
            {tabs.map(
                (
                    {
                        title,
                        disabled = false,
                        hasTabError = false,
                        key,
                        disabledMessage,
                    },
                    index,
                ) => (
                    <PolioDialogTab
                        key={key}
                        title={title}
                        disabled={disabled}
                        hasTabError={hasTabError}
                        handleChange={handleChange}
                        value={index}
                        disabledMessage={disabledMessage}
                    />
                ),
            )}
        </Tabs>
    );
};
