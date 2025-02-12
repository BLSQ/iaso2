import React, { useContext } from 'react';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import MenuIcon from '@mui/icons-material/Menu';
import { Box, Grid, IconButton, useMediaQuery, useTheme } from '@mui/material';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import { makeStyles } from '@mui/styles';
import PropTypes from 'prop-types';
import { useSidebar } from '../../domains/app/contexts/SideBarContext.tsx';
import { ThemeConfigContext } from '../../domains/app/contexts/ThemeConfigContext.tsx';
import { LangSwitch } from '../../domains/home/components/LangSwitch';
import { useCurrentUser } from '../../utils/usersUtils.ts';
import { CurrentUserInfos } from './CurrentUser/index.tsx';
import { HomePageButton } from './HomePageButton.tsx';
import { LogoutButton } from './LogoutButton.tsx';

const styles = theme => ({
    menuButton: {
        [theme.breakpoints.up('md')]: {
            marginRight: `${theme.spacing(2)} !important`,
            marginLeft: `${theme.spacing(1)} !important`,
        },
    },
    version: {
        fontSize: 9,
        display: 'block',
        marginTop: 5,
    },

    root: {
        '&.MuiToolbar-gutters': {
            paddingRight: '48px',
        },
    },
    logoutButton: {
        padding: theme.spacing(0),
    },
});

const useStyles = makeStyles(styles);

function TopBar(props) {
    const {
        title,
        children,
        displayBackButton,
        goBack,
        displayMenuButton,
        disableShadow,
    } = props;
    const classes = useStyles();

    const { APP_TITLE } = useContext(ThemeConfigContext);
    // Set the page title from the top bar title.
    React.useEffect(() => {
        document.title = `${APP_TITLE} ${title ? `| ${title}` : ''}`;
    }, [title, APP_TITLE]);
    const { toggleSidebar } = useSidebar();

    const currentUser = useCurrentUser();
    const theme = useTheme();
    const isMobileLayout = useMediaQuery(theme.breakpoints.down('md'));

    return (
        <AppBar
            position="relative"
            color="primary"
            id="top-bar"
            sx={{ zIndex: 10 }}
            elevation={disableShadow ? 0 : 4}
        >
            <Toolbar className={classes.root}>
                <Grid
                    container
                    justifyContent="space-between"
                    alignItems="center"
                    direction="row"
                >
                    <Grid
                        container
                        item
                        direction="row"
                        xs={7}
                        alignItems="center"
                    >
                        {!displayBackButton && displayMenuButton && (
                            <IconButton
                                className={classes.menuButton}
                                color="inherit"
                                aria-label="Menu"
                                onClick={toggleSidebar}
                                id="menu-button"
                            >
                                <MenuIcon />
                            </IconButton>
                        )}
                        {displayBackButton && (
                            <IconButton
                                className={classes.menuButton}
                                color="inherit"
                                aria-label="Back"
                                onClick={goBack}
                                id="top-bar-back-button"
                            >
                                <ArrowBackIcon />
                            </IconButton>
                        )}
                        <Typography
                            variant="h6"
                            color="inherit"
                            id="top-bar-title"
                        >
                            {title}
                        </Typography>
                    </Grid>
                    {currentUser && !isMobileLayout && (
                        <Grid container item xs={5} justifyContent="flex-end">
                            <Box
                                display="flex"
                                alignItems="center"
                                justifyContent="flex-end"
                            >
                                <CurrentUserInfos
                                    currentUser={currentUser}
                                    version={window.IASO_VERSION}
                                />
                            </Box>

                            <Box display="flex" justifyContent="center" pl={2}>
                                <HomePageButton />
                            </Box>

                            <Box display="flex" justifyContent="center" pl={1}>
                                <LogoutButton />
                            </Box>
                            <Box
                                display="flex"
                                justifyContent="center"
                                alignItems="center"
                                pl={1}
                            >
                                <LangSwitch />
                            </Box>
                        </Grid>
                    )}
                </Grid>
            </Toolbar>
            {children}
        </AppBar>
    );
}

TopBar.defaultProps = {
    children: null,
    displayBackButton: false,
    goBack: () => null,
    title: '',
    displayMenuButton: true,
    disableShadow: false,
};

TopBar.propTypes = {
    title: PropTypes.string,
    children: PropTypes.any,
    displayBackButton: PropTypes.bool,
    goBack: PropTypes.func,
    displayMenuButton: PropTypes.bool,
    disableShadow: PropTypes.bool,
};

export default TopBar;
