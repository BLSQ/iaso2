import { textPlaceholder } from 'bluesquare-components';
import React, { useCallback } from 'react';

import { getChipColors } from '../../constants/chipColors';
import { baseUrls } from '../../constants/urls';
import { orderOrgUnitsByDepth } from '../../utils/map/mapUtils.ts';
import { useGetOrgUnitValidationStatus } from './hooks/utils/useGetOrgUnitValidationStatus.ts';
import MESSAGES from './messages.ts';

export const getLatestOrgUnitLevelId = levels => {
    if (levels) {
        const levelsIds = levels.split(',');
        const latestId = parseInt(levelsIds[levelsIds.length - 1], 10);
        return latestId;
    }
    return null;
};

export const getOrgUnitsTree = orgUnit => {
    let tree = [orgUnit];
    const orgUnitLoop = (parent, tempTree) => {
        let treeCopy = [parent, ...tempTree];
        if (parent.parent) {
            treeCopy = orgUnitLoop(parent.parent, treeCopy);
        }
        return treeCopy;
    };

    if (orgUnit.parent) {
        tree = orgUnitLoop(orgUnit.parent, tree);
    }
    return tree;
};

export const getAliasesArrayFromString = aliasString =>
    aliasString.replace('[', '').replace(']', '').replace(/"/gi, '').split(',');

export const getSourcesWithoutCurrentSource = (
    sourcesList,
    currentSourceId,
) => {
    const sources = [];
    sourcesList.forEach(s => {
        if (s.id !== currentSourceId) {
            sources.push(s);
        }
    });
    return sources;
};

export const orgUnitLabelString = (
    orgUnit,
    withType,
    formatMessage,
    withSource = true,
) => {
    let message = textPlaceholder;
    if (orgUnit && orgUnit.name) {
        message = orgUnit.name;
        if (orgUnit.source && withSource) {
            message += ` - ${formatMessage(MESSAGES.sourceLower)}: ${
                orgUnit.source
            }`;
        }
        if (orgUnit.org_unit_type_name && withType) {
            message += ` (${orgUnit.org_unit_type_name})`;
        }
    }
    return message;
};

const mapOrgUnitBySearch = (orgUnits, searches) => {
    const mappedOrgunits = [];
    searches.forEach((search, i) => {
        mappedOrgunits[i] = orgUnits.filter(o => o.search_index === i);
    });
    return mappedOrgunits;
};

export const mapOrgUnitByLocation = (orgUnits, searches) => {
    let shapes = orgUnits.filter(o => Boolean(o.geo_json));
    let locations = orgUnits.filter(o => Boolean(o.latitude && o.longitude));
    shapes = orderOrgUnitsByDepth(shapes);
    locations = orderOrgUnitsByDepth(locations);
    const mappedOrgunits = {
        shapes,
        locations,
    };
    mappedOrgunits.locations = mapOrgUnitBySearch(
        mappedOrgunits.locations,
        searches,
    );
    return mappedOrgunits;
};

export const getColorsFromParams = params => {
    const searches = JSON.parse(params.searches);
    return searches.map(s => s.color);
};

export const decodeSearch = search => {
    try {
        return JSON.parse(search);
    } catch (e) {
        console.warn(e);
        return [];
    }
};

export const encodeUriSearches = searches => {
    const newSearches = [...searches];
    newSearches.forEach((s, i) => {
        Object.keys(s).forEach(key => {
            const value = s[key];
            newSearches[i][key] =
                key === 'search' ? encodeURIComponent(value) : value;
        });
    });
    return JSON.stringify(newSearches);
};

export const encodeUriParams = params => {
    const searches = encodeUriSearches([...decodeSearch(params.searches)]);
    const newParams = {
        ...params,
        searches,
    };
    return newParams;
};

export const useGetStatusMessage = () => {
    const { data: validationStatusOptions } = useGetOrgUnitValidationStatus();
    const getStatusMessage = useCallback(
        status => {
            if (!validationStatusOptions) return '';
            return (
                validationStatusOptions.find(option => option.value === status)
                    ?.label ?? ''
            );
        },
        [validationStatusOptions],
    );
    return getStatusMessage;
};
export const getOrgUnitGroups = orgUnit => (
    <span>
        {orgUnit.groups &&
            orgUnit.groups.length > 0 &&
            orgUnit.groups.map(g => g.name).join(', ')}
        {(!orgUnit.groups || orgUnit.groups.length === 0) && textPlaceholder}
    </span>
);

export const getOrgUnitProjects = orgUnit => (
    <span>
        {orgUnit.projects?.length > 0
            ? orgUnit.projects.map(project => project.name).join(', ')
            : textPlaceholder}
    </span>
);

export const getLinksSources = (links, coloredSources, currentOrgUnit) => {
    let sources = [];
    links?.forEach(l => {
        const tempSources = getSourcesWithoutCurrentSource(
            coloredSources,
            currentOrgUnit.source_id,
        );
        const isSelectedSource = sourceId =>
            sources.find(ss => ss.id === sourceId);
        // getting the org unit source linked to current one and preselect them
        const linkSources = tempSources.filter(
            s =>
                (s.id === l.source.source_id &&
                    !isSelectedSource(l.source.source_id)) ||
                (s.id === l.destination.source_id &&
                    !isSelectedSource(l.destination.source_id)),
        );
        if (linkSources.length > 0) {
            sources = sources.concat(linkSources);
        }
    });
    return sources;
};

export const filterOrgUnitsByGroupUrl = groupId => {
    const defaultChipColor = getChipColors(0).replace('#', '');
    return (
        `/${baseUrls.orgUnits}/locationLimit/3000/order/id` +
        `/pageSize/50/page/1/searchTabIndex/0/searchActive/true` +
        `/searches/[{"validation_status":"all", "color":"${defaultChipColor}", "group":"${groupId}", "source": null}]`
    );
};
