import React, { FunctionComponent, useState } from 'react';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ContactSupportIcon from '@mui/icons-material/ContactSupport';
import ExitIcon from '@mui/icons-material/ExitToApp';
import { Box, Button, Paper, Typography } from '@mui/material';
import { makeStyles } from '@mui/styles';

import { useSafeIntl } from 'bluesquare-components';
import { useFormik } from 'formik';
import { isEqual } from 'lodash';
import InputComponent from '../../components/forms/InputComponent';
import TopBar from '../../components/nav/TopBarComponent';
import {
    useApiErrorValidation,
    useTranslatedErrors,
} from '../../libs/validation';
import { commaSeparatedIdsToStringArray } from '../../utils/forms';
import getDisplayName, { useCurrentUser } from '../../utils/usersUtils';
import { useGetModulesDropDown } from './hooks/useGetModulesDropDown';
import { useSaveAccount } from './hooks/useSaveAccount';
import { MESSAGES } from './messages';
import { SaveAccountQuery } from './types/account';
import { useAccountValidation } from './validation';

const useStyles = makeStyles(theme => ({
    paper: {
        margin: `auto`,
        width: 500,
        padding: theme.spacing(2),
        marginTop: theme.spacing(4),
    },
    icon: {
        // @ts-ignore
        color: theme.palette.ligthGray.border,
        fontWeight: 100,
        fontSize: 150,
    },
    confirmMessage: {
        color: theme.palette.success.main,
    },
    confirmMessageIcon: {
        fontSize: 120,
        display: 'block',
        marginRight: theme.spacing(1),
        position: 'relative',
        top: 5,
    },
}));

export const SetupAccount: FunctionComponent = () => {
    const currentUser = useCurrentUser();
    const [isSaved, setIsSaved] = useState<boolean>(false);
    const { formatMessage } = useSafeIntl();
    const classes: Record<string, string> = useStyles();
    const isAdmin = currentUser.is_superuser || currentUser.is_staff;

    const { mutateAsync: saveAccount, isLoading } = useSaveAccount();
    const {
        apiErrors,
        payload,
        mutation: save,
    } = useApiErrorValidation<SaveAccountQuery, any>({
        mutationFn: saveAccount,
        onSuccess: () => {
            setIsSaved(true);
        },
    });
    const schema = useAccountValidation(apiErrors, payload);
    const formik = useFormik({
        initialValues: {
            account_name: '',
            user_username: '',
            user_first_name: '',
            user_last_name: '',
            password: '',
            modules: [],
        },
        enableReinitialize: true,
        validateOnBlur: true,
        validationSchema: schema,
        onSubmit: save,
    });

    const {
        values,
        setFieldValue,
        setFieldTouched,
        errors,
        touched,
        isValid,
        initialValues,
        handleSubmit,
    } = formik;
    const onChange = (keyValue, value) => {
        setFieldTouched(keyValue, true);
        if (keyValue === 'modules' && value) {
            setFieldValue(keyValue, commaSeparatedIdsToStringArray(value));
        } else {
            setFieldValue(keyValue, value);
        }
    };

    const getErrors = useTranslatedErrors({
        errors,
        formatMessage,
        touched,
        messages: MESSAGES,
    });

    const { data: modules, isFetching: isFetchingModules } =
        useGetModulesDropDown();

    const allowConfirm = isValid && !isEqual(values, initialValues);
    return (
        <>
            <TopBar
                displayBackButton={false}
                displayMenuButton={false}
                title={formatMessage(MESSAGES.welcome)}
            />
            <Paper className={classes.paper}>
                {isAdmin && (
                    <>
                        {isSaved && (
                            <>
                                <Typography
                                    variant="h6"
                                    className={classes.confirmMessage}
                                >
                                    <CheckCircleOutlineIcon
                                        className={classes.confirmMessageIcon}
                                    />
                                    {formatMessage(MESSAGES.confirmMessage)}
                                </Typography>
                                <Box
                                    mt={2}
                                    display="flex"
                                    justifyContent="flex-end"
                                >
                                    <Button
                                        size="small"
                                        color="primary"
                                        href="/logout-iaso"
                                        variant="contained"
                                    >
                                        <Box
                                            mr={1}
                                            display="flex"
                                            alignContent="center"
                                        >
                                            <ExitIcon fontSize="small" />
                                        </Box>
                                        {formatMessage(MESSAGES.logout)}
                                    </Button>
                                </Box>
                            </>
                        )}
                        {!isSaved && (
                            <>
                                <Typography variant="h5" color="primary">
                                    {formatMessage(MESSAGES.accountSetup)}
                                </Typography>
                                <Box>
                                    <InputComponent
                                        type="text"
                                        required
                                        keyValue="account_name"
                                        labelString={formatMessage(
                                            MESSAGES.account_name,
                                        )}
                                        value={values.account_name}
                                        onChange={onChange}
                                        errors={getErrors('account_name')}
                                    />
                                    <InputComponent
                                        type="text"
                                        required
                                        keyValue="user_username"
                                        labelString={formatMessage(
                                            MESSAGES.user_username,
                                        )}
                                        value={values.user_username}
                                        onChange={onChange}
                                        errors={getErrors('user_username')}
                                    />
                                    <InputComponent
                                        type="text"
                                        required
                                        keyValue="user_first_name"
                                        labelString={formatMessage(
                                            MESSAGES.user_first_name,
                                        )}
                                        value={values.user_first_name}
                                        onChange={onChange}
                                    />
                                    <InputComponent
                                        type="text"
                                        required
                                        keyValue="user_last_name"
                                        labelString={formatMessage(
                                            MESSAGES.user_last_name,
                                        )}
                                        value={values.user_last_name}
                                        onChange={onChange}
                                    />
                                    <InputComponent
                                        type="password"
                                        required
                                        keyValue="password"
                                        labelString={formatMessage(
                                            MESSAGES.password,
                                        )}
                                        value={values.password}
                                        onChange={onChange}
                                        errors={getErrors('password')}
                                    />
                                    <InputComponent
                                        type="select"
                                        multi
                                        required
                                        keyValue="modules"
                                        labelString={formatMessage(
                                            MESSAGES.modules,
                                        )}
                                        value={values.modules}
                                        onChange={onChange}
                                        errors={getErrors('modules')}
                                        loading={isFetchingModules}
                                        options={modules ?? []}
                                    />
                                    <Box
                                        mt={2}
                                        display="flex"
                                        justifyContent="flex-end"
                                    >
                                        <Button
                                            data-test="confirm-button"
                                            onClick={() => handleSubmit()}
                                            disabled={
                                                !allowConfirm || isLoading
                                            }
                                            color="primary"
                                            autoFocus
                                            variant="contained"
                                        >
                                            {formatMessage(MESSAGES.confirm)}
                                        </Button>
                                    </Box>
                                </Box>
                            </>
                        )}
                    </>
                )}
                {!isAdmin && (
                    <Box textAlign="center">
                        <Box
                            pt={2}
                            pb={2}
                            display="flex"
                            justifyContent="center"
                            flexDirection="column"
                        >
                            <Typography variant="h6">
                                {formatMessage(MESSAGES.notAdmin, {
                                    displayName: getDisplayName(currentUser),
                                })}
                            </Typography>
                            <Typography>
                                {formatMessage(MESSAGES.notAdmin2)}
                            </Typography>
                        </Box>
                        <ContactSupportIcon className={classes.icon} />
                    </Box>
                )}
            </Paper>
        </>
    );
};
