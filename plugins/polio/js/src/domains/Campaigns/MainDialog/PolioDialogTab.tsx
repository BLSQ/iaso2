import React, { FunctionComponent, useCallback } from 'react';
import InfoIcon from '@mui/icons-material/Info';
import { Tab, Tooltip } from '@mui/material';

import classnames from 'classnames';
import { useStyles } from '../../../styles/theme';

type Props = {
    value: number;
    title: string;
    hasTabError: boolean;
    disabled: boolean;
    handleChange: (_event: any, newValue: number) => void;
    disabledMessage?: string;
};

export const PolioDialogTab: FunctionComponent<Props> = ({
    value,
    title,
    hasTabError,
    disabled,
    handleChange,
    disabledMessage,
}) => {
    const classes: Record<string, string> = useStyles();
    const onChange = useCallback(() => {
        if (!disabled) {
            handleChange(undefined, value);
        }
    }, [disabled, handleChange, value]);

    return (
        <Tab
            label={title}
            onClick={onChange}
            className={classnames(
                classes.tab,
                hasTabError && classes.tabError,
                disabled && classes.tabDisabled,
            )}
            disableFocusRipple={disabled}
            disableRipple={disabled}
            iconPosition="end"
            icon={
                (disabled && disabledMessage && (
                    <Tooltip title={disabledMessage}>
                        <InfoIcon
                            fontSize="small"
                            className={classes.tabIcon}
                        />
                    </Tooltip>
                )) || <></>
            }
        />
    );
};
