import React, { FunctionComponent, useCallback } from 'react';
import { Box, Button } from '@mui/material';
import { makeStyles } from '@mui/styles';
import classNames from 'classnames';
import { useHasNoAccount } from '../../../utils/usersUtils';
import { APP_LOCALES } from '../../app/constants';
import { useLocale } from '../../app/contexts/LocaleContext';
import { useSaveCurrentUser } from '../../users/hooks/useSaveCurrentUser';

const useStyles = makeStyles(theme => ({
    languageSwitch: {
        display: 'inline-block',
        textTransform: 'uppercase',
        cursor: 'pointer',
        padding: theme.spacing(0, 0.5),
        color: '#ffffff',
    },
    languageSwitchButton: {
        backgroundColor: theme.palette.success.main,
        color: 'white',
        borderRadius: 0,
        textTransform: 'none',
        paddingLeft: theme.spacing(3),
        paddingRight: theme.spacing(3),
    },
    languageSwithActive: {
        color: theme.palette.secondary.light,
        cursor: 'text',
    },
}));

type Props = {
    topBar?: boolean;
};

export const LangSwitch: FunctionComponent<Props> = () => {
    const classes: Record<string, string> = useStyles();
    const { mutate: saveCurrentUser } = useSaveCurrentUser(false);
    const hasNoAccount = useHasNoAccount();
    const { locale: activeLocale } = useLocale();
    const { setLocale } = useLocale();
    const handleClick = useCallback(
        localeCode => {
            setLocale(localeCode);
            if (!hasNoAccount) {
                saveCurrentUser({
                    language: localeCode,
                });
            }
        },
        [hasNoAccount, setLocale, saveCurrentUser],
    );
    return (
        <>
            {APP_LOCALES.map((locale, index) => {
                return (
                    <Box key={locale.code}>
                        <Box
                            className={classNames(classes.languageSwitch, {
                                [classes.languageSwithActive]:
                                    locale.code === activeLocale,
                            })}
                            onClick={() => handleClick(locale.code)}
                        >
                            {locale.code}
                        </Box>

                        {index + 1 !== APP_LOCALES.length && '-'}
                    </Box>
                );
            })}
        </>
    );
};

// We don't need to translate as we show "English" in english etc
const localeMap = {
    fr: 'Français',
    en: 'English',
};

export const OffLineLangSwitch: FunctionComponent = () => {
    const classes: Record<string, string> = useStyles();
    const { setLocale } = useLocale();
    const handleClick = useCallback(
        localeCode => {
            setLocale(localeCode);
        },
        [setLocale],
    );
    return (
        <>
            {APP_LOCALES.map((locale, index) => {
                return (
                    <Box key={locale.code} ml={index === 1 ? 2 : undefined}>
                        <Button
                            onClick={() => handleClick(locale.code)}
                            className={classes.languageSwitchButton}
                        >
                            {localeMap[locale.code]}
                        </Button>
                    </Box>
                );
            })}
        </>
    );
};
