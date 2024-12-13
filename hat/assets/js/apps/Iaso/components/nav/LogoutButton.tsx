import React, { FunctionComponent } from 'react';
import { IconButton as MuiIconButton, Tooltip } from '@mui/material';
import { makeStyles } from '@mui/styles';
import ExitIcon from '@mui/icons-material/ExitToApp';
import { useSafeIntl } from 'bluesquare-components';
import Cookies from 'js-cookie';
import { iasoFetch } from '../../libs/Api';

import MESSAGES from './messages';
import { openSnackBar } from '../snackBars/EventDispatcher';
import { errorSnackBar } from '../../constants/snackBars';
import snackBarMessages from '../snackBars/messages';

const useStyles = makeStyles(theme => ({
    logoutButton: {
        padding: theme.spacing(0),
    },
}));

type Props = {
    color?: 'inherit' | 'primary' | 'secondary';
};

export const LogoutButton: FunctionComponent<Props> = ({
    color = 'inherit',
}) => {
    const handleLogout = () => {
        iasoFetch('/logout-iaso', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': Cookies.get("csrftoken"),
            },
        })
            .then(() => {
                window.location.href = '/login';
            })
            .catch(error => {
                openSnackBar(
                    errorSnackBar(
                        'iaso.snackBar.logoutError',
                        snackBarMessages.logoutError,
                        error,
                    ),
                );
                console.error(`Error while logging out:`, error);
            });
    };

    const classes = useStyles();
    const { formatMessage } = useSafeIntl();
    return (
        <Tooltip arrow title={formatMessage(MESSAGES.logout)}>
            <MuiIconButton
                className={classes.logoutButton}
                color={color}
                id="top-bar-logout-button"
                onClick={handleLogout}
            >
                <ExitIcon />
            </MuiIconButton>
        </Tooltip>
    );
};
