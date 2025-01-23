import { Box, Grid, Tab, Tabs } from '@mui/material';
import { alpha } from '@mui/material/styles';
import { makeStyles } from '@mui/styles';
import {
    LoadingSpinner,
    commonStyles,
    useGoBack,
    useRedirectToReplace,
    useSafeIntl,
} from 'bluesquare-components';
import omit from 'lodash/omit';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useQueryClient } from 'react-query';
import TopBar from '../../components/nav/TopBarComponent';
import {
    FORMS_PREFIX,
    LINKS_PREFIX,
    OU_CHILDREN_PREFIX,
    baseUrls,
} from '../../constants/urls.ts';
import { useParamsObject } from '../../routing/hooks/useParamsObject.tsx';
import { useCheckUserHasWritePermissionOnOrgunit } from '../../utils/usersUtils.ts';
import { FormsTable } from '../forms/components/FormsTable.tsx';
import { OrgUnitForm } from './components/OrgUnitForm.tsx';
import { OrgUnitImages } from './components/OrgUnitImages.tsx';
import { OrgUnitsMapComments } from './components/orgUnitMap/OrgUnitComments/OrgUnitsMapComments';
import { OrgUnitMap } from './components/orgUnitMap/OrgUnitMap/OrgUnitMap.tsx';
import { OrgUnitChildren } from './details/Children/OrgUnitChildren.tsx';
import { OrgUnitLinks } from './details/Links/OrgUnitLinks.tsx';
import { Logs } from './history/LogsComponent.tsx';
import { wktToGeoJSON } from './history/LogValue.tsx';
import {
    useOrgUnitDetailData,
    useOrgUnitTabParams,
    useRefreshOrgUnit,
    useSaveOrgUnit,
} from './hooks';
import MESSAGES from './messages.ts';
import { fetchAssociatedOrgUnits } from './requests';
import {
    getAliasesArrayFromString,
    getLinksSources,
    getOrgUnitsTree,
} from './utils';

const baseUrl = baseUrls.orgUnitDetails;
const useStyles = makeStyles(theme => ({
    ...commonStyles(theme),
    root: {
        '& path.primary': {
            fill: alpha(theme.palette.primary.main, 0.6),
            stroke: theme.palette.primary.main,
            strokeOpacity: 1,
            strokeWidth: 3,
        },
        '& path.secondary': {
            fill: alpha(theme.palette.secondary.main, 0.6),
            stroke: theme.palette.secondary.main,
            strokeOpacity: 1,
            strokeWidth: 3,
        },
    },
    comments: {
        overflowY: 'auto',
        height: '65vh',
    },
    commentsWrapper: {
        backgroundColor: 'white',
        paddingTop: '10px',
    },
    hiddenOpacity: {
        position: 'absolute',
        top: '0px',
        left: '0px',
        width: '100vw',
        zIndex: '-100',
        opacity: '0',
    },
}));

const initialOrgUnit = {
    id: null,
    name: '',
    org_unit_type_id: null,
    groups: [],
    sub_source: null,
    status: false,
    aliases: [],
};

const tabs = [
    'infos',
    'map',
    'children',
    'links',
    'history',
    'forms',
    'images',
    'comments',
];

const OrgUnitDetail = () => {
    const classes = useStyles();
    const params = useParamsObject(baseUrl);
    const goBack = useGoBack(baseUrls.orgUnits);
    const { mutateAsync: saveOu, isLoading: savingOu } = useSaveOrgUnit();
    const queryClient = useQueryClient();
    const { formatMessage } = useSafeIntl();
    const refreshOrgUnitQueryCache = useRefreshOrgUnit();
    const redirectToReplace = useRedirectToReplace();

    const [currentOrgUnit, setCurrentOrgUnit] = useState(null);
    const [sourcesSelected, setSourcesSelected] = useState(undefined);
    const [loadingSelectedSources, setLoadingSelectedSources] =
        useState(undefined);
    const [orgUnitLocationModified, setOrgUnitLocationModified] =
        useState(false);

    const showLogButtons = useCheckUserHasWritePermissionOnOrgunit(
        currentOrgUnit?.org_unit_type_id,
    );
    const formParams = useOrgUnitTabParams(params, FORMS_PREFIX);
    const linksParams = useOrgUnitTabParams(params, LINKS_PREFIX);
    const childrenParams = useOrgUnitTabParams(params, OU_CHILDREN_PREFIX);

    const isNewOrgunit = params.orgUnitId === '0';

    const title = useMemo(() => {
        if (isNewOrgunit) {
            return formatMessage(MESSAGES.newOrgUnit);
        }
        if (currentOrgUnit?.org_unit_type_name) {
            return (
                `${currentOrgUnit?.name}${
                    currentOrgUnit.org_unit_type_name
                        ? ` - ${currentOrgUnit.org_unit_type_name}`
                        : ''
                }` ?? ''
            );
        }
        return currentOrgUnit?.name ?? '';
    }, [
        currentOrgUnit?.name,
        currentOrgUnit?.org_unit_type_name,
        formatMessage,
        isNewOrgunit,
    ]);

    const handleResetOrgUnit = async () => {
        const newParams = {
            ...params,
            levels: null,
        };
        redirectToReplace(baseUrl, newParams);
        queryClient.invalidateQueries('currentOrgUnit');
    };

    const handleChangeTab = useCallback(
        newTab => {
            const newParams = {
                ...params,
                tab: newTab,
            };
            redirectToReplace(baseUrl, newParams);
        },
        [params, redirectToReplace],
    );

    const handleChangeShape = useCallback(
        (geoJson, key) => {
            setOrgUnitLocationModified(true);
            setCurrentOrgUnit({
                ...currentOrgUnit,
                [key]: geoJson,
            });
        },
        [currentOrgUnit],
    );
    const handleChangeLocation = useCallback(
        location => {
            setOrgUnitLocationModified(true);
            const { latitude, longitude, altitude } = location;
            setCurrentOrgUnit({
                ...currentOrgUnit,
                altitude,
                longitude,
                latitude,
            });
        },
        [currentOrgUnit],
    );

    const {
        groups,
        orgUnitTypes,
        links,
        sources,
        isFetchingDatas,
        originalOrgUnit,
        isFetchingDetail,
        isFetchingOrgUnitTypes,
        isFetchingGroups,
        parentOrgUnit,
        isFetchingSources,
    } = useOrgUnitDetailData(
        isNewOrgunit,
        params.orgUnitId,
        setCurrentOrgUnit,
        params.levels,
        params.tab,
    );
    const goToRevision = useCallback(
        (orgUnitRevision, onSuccess) => {
            const {
                location,
                aliases: revisionAliases,
                ...revision
            } = orgUnitRevision.fields;

            const coordinates = location
                ? (wktToGeoJSON(location)?.coordinates ?? [])
                : [];
            const [longitude, latitude] = coordinates;
            const aliases = revisionAliases
                ? getAliasesArrayFromString(orgUnitRevision.fields.aliases)
                : currentOrgUnit.aliases;
            const mappedRevision = {
                ...currentOrgUnit,
                ...revision,
                location,
                geo_json: null, // this line to prevent overwriting the geo_json with a simplified shape/ Disables restoring a previous version of a single shape
                aliases,
                id: currentOrgUnit.id,
            };
            // This block to avoid sending undefined to the API
            if (latitude) {
                mappedRevision.latitude = latitude;
            }
            if (longitude) {
                mappedRevision.longitude = longitude;
            }
            // end
            // Retrieve only the group ids as it's what the API expect
            const group_ids = mappedRevision.groups.map(g => g.id);
            mappedRevision.groups = group_ids;
            saveOu(mappedRevision).then(res => {
                refreshOrgUnitQueryCache(res);
                onSuccess();
            });
        },
        [currentOrgUnit, refreshOrgUnitQueryCache, saveOu],
    );

    const handleSaveOrgUnit = useCallback(
        (newOrgUnit = {}, onSuccess = () => {}, onError = () => {}) => {
            let orgUnitPayload = omit({ ...currentOrgUnit, ...newOrgUnit });
            orgUnitPayload = {
                ...orgUnitPayload,
                groups:
                    orgUnitPayload.groups.length > 0 &&
                    !orgUnitPayload.groups[0].id
                        ? orgUnitPayload.groups
                        : orgUnitPayload.groups.map(g => g.id),
            };
            saveOu(orgUnitPayload)
                .then(ou => {
                    setCurrentOrgUnit(ou);
                    setOrgUnitLocationModified(false);
                    if (isNewOrgunit) {
                        redirectToReplace(baseUrl, {
                            ...params,
                            orgUnitId: ou.id,
                        });
                    }
                    refreshOrgUnitQueryCache(ou);
                    onSuccess(ou);
                })
                .catch(onError);
        },
        [
            currentOrgUnit,
            isNewOrgunit,
            params,
            redirectToReplace,
            refreshOrgUnitQueryCache,
            saveOu,
        ],
    );

    useEffect(() => {
        if (!params.tab) {
            redirectToReplace(baseUrl, { ...params, tab: 'infos' });
        }
    }, [params, redirectToReplace]);

    useEffect(() => {
        if (isNewOrgunit && !currentOrgUnit) {
            if (params.levels && parentOrgUnit) {
                setCurrentOrgUnit({
                    ...initialOrgUnit,
                    parent: parentOrgUnit,
                });
            } else if (!params.levels) {
                setCurrentOrgUnit(initialOrgUnit);
            }
        }
    }, [parentOrgUnit, isNewOrgunit, params.levels, currentOrgUnit]);

    // Set levels params in the url
    useEffect(() => {
        if (originalOrgUnit && !isNewOrgunit && !params.levels) {
            const orgUnitTree = getOrgUnitsTree(originalOrgUnit);
            if (orgUnitTree.length > 0) {
                const levels = orgUnitTree.map(o => o.id);
                const newParams = {
                    ...params,
                    levels,
                };
                if (params.levels !== levels.join(',') && levels.length > 0) {
                    redirectToReplace(baseUrl, newParams);
                }
            }
        }
    }, [originalOrgUnit, isNewOrgunit, params, redirectToReplace]);

    // Set selected sources for current org unit
    useEffect(() => {
        if (originalOrgUnit && !isNewOrgunit && !sourcesSelected) {
            const selectedSources = getLinksSources(
                links,
                sources,
                originalOrgUnit,
            );
            const fullSelectedSources = [];
            if (selectedSources.length === 0) {
                setLoadingSelectedSources(false);
            }
            for (let i = 0; i < selectedSources.length; i += 1) {
                const ss = selectedSources[i];
                setLoadingSelectedSources(true);
                // eslint-disable-next-line no-await-in-loop
                const fetch = async () => {
                    const ous = await fetchAssociatedOrgUnits(
                        ss,
                        originalOrgUnit,
                    );
                    fullSelectedSources.push(ous);
                    if (i + 1 === selectedSources.length) {
                        setSourcesSelected(fullSelectedSources);
                        setLoadingSelectedSources(false);
                    }
                };
                fetch();
            }
        }
    }, [originalOrgUnit, links, sources, isNewOrgunit, sourcesSelected]);
    return (
        <section className={classes.root}>
            <TopBar title={title} displayBackButton goBack={goBack}>
                {!isNewOrgunit && (
                    <Tabs
                        textColor="inherit"
                        indicatorColor="secondary"
                        value={params.tab}
                        classes={{
                            root: classes.tabs,
                            indicator: classes.indicator,
                        }}
                        onChange={(event, newtab) => handleChangeTab(newtab)}
                    >
                        {tabs.map(t => (
                            <Tab
                                key={t}
                                value={t}
                                label={formatMessage(MESSAGES[t])}
                            />
                        ))}
                    </Tabs>
                )}
            </TopBar>

            {(isFetchingDetail || isFetchingDatas || savingOu) &&
                (params.tab === 'infos' ||
                    params.tab === 'map' ||
                    params.tab === 'comments') && <LoadingSpinner />}
            {currentOrgUnit && (
                <section>
                    {params.tab === 'infos' && (
                        <Box
                            className={
                                isNewOrgunit
                                    ? classes.containerFullHeightNoTabPadded
                                    : classes.containerFullHeightPadded
                            }
                        >
                            <OrgUnitForm
                                orgUnit={currentOrgUnit}
                                orgUnitTypes={orgUnitTypes}
                                groups={groups}
                                onResetOrgUnit={() => handleResetOrgUnit()}
                                saveOrgUnit={handleSaveOrgUnit}
                                params={params}
                                baseUrl={baseUrl}
                                isFetchingOrgUnitTypes={isFetchingOrgUnitTypes}
                                isFetchingGroups={isFetchingGroups}
                            />
                        </Box>
                    )}
                    {!isNewOrgunit && (
                        <>
                            <div
                                className={
                                    params.tab === 'map'
                                        ? ''
                                        : classes.hiddenOpacity
                                }
                            >
                                <Box className={classes.containerFullHeight}>
                                    {!isFetchingDetail && (
                                        <OrgUnitMap
                                            loadingSelectedSources={
                                                loadingSelectedSources
                                            }
                                            currentOrgUnit={currentOrgUnit}
                                            sources={sources}
                                            orgUnitTypes={orgUnitTypes}
                                            sourcesSelected={sourcesSelected}
                                            setSourcesSelected={newSourcesSelected => {
                                                setSourcesSelected(
                                                    newSourcesSelected,
                                                );
                                            }}
                                            setOrgUnitLocationModified={isModified =>
                                                setOrgUnitLocationModified(
                                                    isModified,
                                                )
                                            }
                                            orgUnitLocationModified={
                                                orgUnitLocationModified
                                            }
                                            resetOrgUnit={() =>
                                                handleResetOrgUnit()
                                            }
                                            saveOrgUnit={() =>
                                                handleSaveOrgUnit()
                                            }
                                            onChangeLocation={
                                                handleChangeLocation
                                            }
                                            onChangeShape={(key, geoJson) =>
                                                handleChangeShape(geoJson, key)
                                            }
                                        />
                                    )}
                                </Box>
                            </div>

                            {params.tab === 'history' && (
                                <div data-test="logs-tab">
                                    <Logs
                                        baseUrl={baseUrl}
                                        params={params}
                                        logObjectId={currentOrgUnit.id}
                                        goToRevision={goToRevision}
                                        showButtons={showLogButtons}
                                    />
                                </div>
                            )}
                            {params.tab === 'images' && (
                                <Box
                                    className={
                                        classes.containerFullHeightNoTabPadded
                                    }
                                    data-test="image-tab"
                                >
                                    <OrgUnitImages
                                        params={params}
                                        orgUnit={originalOrgUnit}
                                        isFetchingDetail={isFetchingDetail}
                                    />
                                </Box>
                            )}
                            {params.tab === 'forms' && (
                                <Box
                                    className={
                                        classes.containerFullHeightNoTabPadded
                                    }
                                    data-test="forms-tab"
                                >
                                    <FormsTable
                                        baseUrl={baseUrl}
                                        params={formParams}
                                        defaultPageSize={10}
                                        paramsPrefix={FORMS_PREFIX}
                                        tableDefaults={{
                                            order: 'name',
                                            limit: 10,
                                            page: 1,
                                        }}
                                    />
                                </Box>
                            )}
                            {params.tab === 'children' && (
                                <Box
                                    data-test="children-tab"
                                    className={
                                        classes.containerFullHeightNoTabPadded
                                    }
                                >
                                    <OrgUnitChildren
                                        baseUrl={baseUrl}
                                        params={childrenParams}
                                        groups={groups}
                                    />
                                </Box>
                            )}
                            {params.tab === 'links' && (
                                <Box
                                    data-test="links-tab"
                                    className={
                                        classes.containerFullHeightNoTabPadded
                                    }
                                >
                                    <OrgUnitLinks
                                        baseUrl={baseUrl}
                                        params={linksParams}
                                        paramsPrefix={LINKS_PREFIX}
                                        sources={sources}
                                        isLoadingSources={isFetchingSources}
                                    />
                                </Box>
                            )}
                            {params.tab === 'comments' && (
                                <div data-test="comments-tab">
                                    <Grid
                                        container
                                        justifyContent="center"
                                        className={classes.commentsWrapper}
                                    >
                                        <Grid item xs={6}>
                                            <OrgUnitsMapComments
                                                className={classes.comments}
                                                orgUnit={currentOrgUnit}
                                                maxPages={4}
                                            />
                                        </Grid>
                                    </Grid>
                                </div>
                            )}
                        </>
                    )}
                </section>
            )}
        </section>
    );
};

export default OrgUnitDetail;
