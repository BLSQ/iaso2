import PropTypes from 'prop-types';
import React, { useEffect } from 'react';
import { useDispatch } from 'react-redux';

import { useLocation, useNavigate, useParams } from 'react-router-dom';
import SidebarMenu from '../../app/components/SidebarMenuComponent';

import { getFirstAllowedUrl, userHasOneOfPermissions } from '../utils';

import PageError from '../../../components/errors/PageError';
import PageNoPerms from '../../../components/errors/PageNoPerms.tsx';
import { hasFeatureFlag } from '../../../utils/featureFlags';
import { useCurrentUser } from '../../../utils/usersUtils.ts';
import { switchLocale } from '../../app/actions';
import { WrongAccountModal } from './WrongAccountModal.tsx';

const ProtectedRoute = ({ routeConfig, allRoutes, component }) => {
    const { featureFlag, permissions, isRootUrl, baseUrl } = routeConfig;
    const params = useParams()['*'];
    const navigate = useNavigate();
    const location = useLocation();
    const currentUser = useCurrentUser();
    const dispatch = useDispatch();

    const isWrongAccount = Boolean(
        params?.accountId && params?.accountId !== `${currentUser.account.id}`,
    );

    let isAuthorized =
        permissions.length > 0
            ? userHasOneOfPermissions(permissions, currentUser)
            : true;
    if (featureFlag && !hasFeatureFlag(currentUser, featureFlag)) {
        isAuthorized = false;
    }
    // TODO merge both effects for simpler redirect
    useEffect(() => {
        if (!isAuthorized && isRootUrl) {
            const newBaseUrl = getFirstAllowedUrl(
                permissions,
                currentUser.permissions ?? [],
                allRoutes,
            );
            if (newBaseUrl) {
                navigate(`./${newBaseUrl}`);
            }
        }
    }, [
        allRoutes,
        currentUser,
        isAuthorized,
        isRootUrl,
        navigate,
        permissions,
    ]);

    useEffect(() => {
        if (!(params ?? '').includes('accountId') && currentUser.account) {
            navigate(`./accountId/${currentUser.account.id}/${params}`, {
                replace: true,
            });
        }
    }, [currentUser.account, baseUrl, navigate, params]);

    useEffect(() => {
        // Use defined default language if it exists and if the user didn't set it manually
        if (currentUser.language) {
            dispatch(switchLocale(currentUser.language));
        }
    }, [currentUser.language, dispatch]);

    // this should kick in if the above effect didn't redirect the user to a better page
    const hasNoPermWarning =
        isRootUrl &&
        (!currentUser.permissions ||
            (currentUser.permissions.length === 0 && !isAuthorized));
    if (!currentUser) {
        return null;
    }
    return (
        <>
            <SidebarMenu location={location} />
            <WrongAccountModal isOpen={isWrongAccount} />
            {isAuthorized && component}
            {hasNoPermWarning && <PageNoPerms />}
            {!isAuthorized && !hasNoPermWarning && (
                <PageError errorCode="403" />
            )}
        </>
    );
};
ProtectedRoute.defaultProps = {
    allRoutes: [],
};

ProtectedRoute.propTypes = {
    component: PropTypes.node.isRequired,
    allRoutes: PropTypes.array,
    routeConfig: PropTypes.object.isRequired,
};

export default ProtectedRoute;
