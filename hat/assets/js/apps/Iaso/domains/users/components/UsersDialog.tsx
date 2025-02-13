import React, {
    FunctionComponent,
    useCallback,
    useEffect,
    useMemo,
    useState,
} from 'react';
import { Tab, Tabs } from '@mui/material';
import { makeStyles } from '@mui/styles';
import {
    AddButton,
    ConfirmCancelModal,
    IntlMessage,
    makeFullModal,
    useSafeIntl,
} from 'bluesquare-components';

import { MutateFunction, useQueryClient } from 'react-query';

import { EditIconButton } from '../../../components/Buttons/EditIconButton';
import * as Permissions from '../../../utils/permissions';
import { Profile, useCurrentUser } from '../../../utils/usersUtils';
import MESSAGES from '../messages';
import { InitialUserData } from '../types';
import PermissionsAttribution from './PermissionsAttribution';
import { useInitialUser } from './useInitialUser';
import { UserOrgUnitWriteTypes } from './UserOrgUnitWriteTypes';
import UsersDialogTabDisabled from './UsersDialogTabDisabled';
import UsersInfos from './UsersInfos';
import UsersLocations from './UsersLocations';
import { WarningModal } from './WarningModal/WarningModal';

const useStyles = makeStyles(theme => ({
    tabs: {
        marginBottom: theme.spacing(3),
    },
    root: {
        position: 'relative',
    },
    hiddenOpacity: {
        position: 'fixed',
        top: 0,
        left: -5000,
        zIndex: -10,
        opacity: 0,
    },
}));

type Props = {
    titleMessage: IntlMessage;
    initialData?: InitialUserData;
    saveProfile: MutateFunction<Profile, any>;
    allowSendEmailInvitation?: boolean;
    isOpen: boolean;
    closeDialog: () => void;
};

// Declaring defaultData here because using initialData={} in the props below will cause and infinite loop
const defaultData: InitialUserData = {};
const UserDialogComponent: FunctionComponent<Props> = ({
    titleMessage,
    isOpen,
    initialData = defaultData,
    saveProfile,
    allowSendEmailInvitation = false,
    closeDialog,
}) => {
    const connectedUser = useCurrentUser();
    const { formatMessage } = useSafeIntl();

    const queryClient = useQueryClient();
    const classes: Record<string, string> = useStyles();

    const { user, setFieldValue, setFieldErrors } = useInitialUser(initialData);
    const [tab, setTab] = useState('infos');
    const [openWarning, setOpenWarning] = useState<boolean>(false);
    const [hasNoOrgUnitManagementWrite, setHasNoOrgUnitManagementWrite] =
        useState<boolean>(false);
    const saveUser = useCallback(() => {
        const currentUser: any = {};
        Object.keys(user).forEach(key => {
            currentUser[key] = user[key].value;
        });
        saveProfile(currentUser, {
            onSuccess: () => {
                if (currentUser.id === connectedUser.id) {
                    queryClient.invalidateQueries('currentUser');
                }
                closeDialog();
            },
            onError: error => {
                if (error.status === 400) {
                    setFieldErrors(
                        error.details.errorKey,
                        error.details.errorMessage,
                    );
                }
            },
        });
    }, [
        closeDialog,
        connectedUser.id,
        queryClient,
        saveProfile,
        setFieldErrors,
        user,
    ]);

    const userPermissions = user?.user_permissions.value ?? [];
    const userRolesPermissions = user?.user_roles_permissions.value ?? [];

    const isPhoneNumberUpdated =
        user.phone_number.value !== initialData.phone_number && user.id?.value;

    const isUserWithoutPermissions =
        userPermissions.length === 0 &&
        userRolesPermissions.length === 0 &&
        !initialData?.is_superuser;

    const onConfirm = useCallback(() => {
        if (
            // If user is not new user and phone number is changed
            isPhoneNumberUpdated ||
            isUserWithoutPermissions
        ) {
            setOpenWarning(true);
        } else {
            saveUser();
        }
    }, [isPhoneNumberUpdated, isUserWithoutPermissions, saveUser]);

    const warningTitleMessage = useMemo(() => {
        if (isPhoneNumberUpdated && isUserWithoutPermissions) {
            return formatMessage(MESSAGES.permAndPhoneWarningTitle);
        }
        if (isPhoneNumberUpdated) {
            return formatMessage(MESSAGES.phoneNumberWarning);
        }
        if (isUserWithoutPermissions) {
            return formatMessage(MESSAGES.createUserWithoutPerm);
        }
        return '';
    }, [formatMessage, isPhoneNumberUpdated, isUserWithoutPermissions]);

    const warningBodyMessage = useMemo(() => {
        if (isPhoneNumberUpdated && isUserWithoutPermissions) {
            return `1/ ${formatMessage(MESSAGES.phoneNumberWarningMessage)}
            2/ ${formatMessage(MESSAGES.warningModalMessage)}`;
        }
        if (isPhoneNumberUpdated) {
            return formatMessage(MESSAGES.phoneNumberWarningMessage);
        }
        if (isUserWithoutPermissions) {
            return formatMessage(MESSAGES.warningModalMessage);
        }
        return '';
    }, [formatMessage, isPhoneNumberUpdated, isUserWithoutPermissions]);

    const allUserRolesPermissions = useMemo(
        () =>
            user.user_roles_permissions.value.flatMap(role => role.permissions),
        [user.user_roles_permissions.value],
    );

    const allUserUserRolesPermissions = useMemo(() => {
        const allUserPermissions = user.user_permissions.value;

        return [
            ...new Set([...allUserPermissions, ...allUserRolesPermissions]),
        ];
    }, [allUserRolesPermissions, user.user_permissions.value]);

    useEffect(() => {
        setHasNoOrgUnitManagementWrite(
            !allUserUserRolesPermissions.includes(Permissions.ORG_UNITS),
        );
    }, [allUserRolesPermissions.length, allUserUserRolesPermissions]);
    return (
        <>
            <WarningModal
                open={openWarning}
                closeDialog={() => setOpenWarning(false)}
                onConfirm={saveUser}
                titleMessage={warningTitleMessage}
                bodyMessage={warningBodyMessage}
            />

            <ConfirmCancelModal
                titleMessage={titleMessage}
                onConfirm={onConfirm}
                cancelMessage={MESSAGES.cancel}
                confirmMessage={MESSAGES.save}
                maxWidth="md"
                open={isOpen}
                closeDialog={() => null}
                allowConfirm={
                    !(
                        user.user_name.value === '' ||
                        (!user.id?.value && user.password.value === '')
                    )
                }
                onClose={() => null}
                onCancel={() => {
                    closeDialog();
                }}
                id="user-dialog"
                dataTestId="user-dialog"
            >
                <Tabs
                    id="user-dialog-tabs"
                    value={tab}
                    classes={{
                        root: classes.tabs,
                    }}
                    onChange={(_event, newtab) => setTab(newtab)}
                >
                    <Tab
                        classes={{
                            root: classes.tab,
                        }}
                        value="infos"
                        label={formatMessage(MESSAGES.infos)}
                    />
                    <Tab
                        classes={{
                            root: classes.tab,
                        }}
                        value="permissions"
                        label={formatMessage(MESSAGES.permissions)}
                    />
                    <Tab
                        classes={{
                            root: classes.tab,
                        }}
                        value="locations"
                        label={formatMessage(MESSAGES.location)}
                    />
                    {hasNoOrgUnitManagementWrite ? (
                        <UsersDialogTabDisabled
                            label={formatMessage(MESSAGES.orgUnitWriteTypes)}
                            disabled
                            tooltipMessage={formatMessage(
                                MESSAGES.OrgUnitTypeWriteDisableTooltip,
                                { type: formatMessage(MESSAGES.user) },
                            )}
                        />
                    ) : (
                        <Tab
                            classes={{
                                root: classes.tab,
                            }}
                            value="orgUnitWriteTypes"
                            label={formatMessage(MESSAGES.orgUnitWriteTypes)}
                        />
                    )}
                </Tabs>
                <div className={classes.root} id="user-profile-dialog">
                    <div
                        className={tab === 'infos' ? '' : classes.hiddenOpacity}
                    >
                        <UsersInfos
                            setFieldValue={(key, value) =>
                                setFieldValue(key, value)
                            }
                            initialData={initialData}
                            currentUser={user}
                            allowSendEmailInvitation={allowSendEmailInvitation}
                        />
                    </div>
                    {tab === 'permissions' && (
                        <PermissionsAttribution
                            isSuperUser={initialData?.is_superuser}
                            currentUser={user}
                            handleChange={permissions => {
                                setFieldValue('user_permissions', permissions);
                            }}
                            setFieldValue={(key, value) =>
                                setFieldValue(key, value)
                            }
                        />
                    )}
                    {tab === 'locations' && (
                        <UsersLocations
                            handleChange={ouList =>
                                setFieldValue('org_units', ouList)
                            }
                            currentUser={user}
                        />
                    )}
                    {tab === 'orgUnitWriteTypes' && (
                        <UserOrgUnitWriteTypes
                            currentUser={user}
                            handleChange={(ouTypesIds: number[]) =>
                                setFieldValue(
                                    'editable_org_unit_type_ids',
                                    ouTypesIds,
                                )
                            }
                        />
                    )}
                </div>
            </ConfirmCancelModal>
        </>
    );
};

const modalWithButton = makeFullModal(UserDialogComponent, AddButton);
const modalWithIcon = makeFullModal(UserDialogComponent, EditIconButton);

export { modalWithButton as AddUsersDialog, modalWithIcon as EditUsersDialog };
