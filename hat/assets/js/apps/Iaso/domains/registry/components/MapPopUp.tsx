import React, { FunctionComponent, useRef } from 'react';
import { Popup } from 'react-leaflet';

import { Card, CardContent, Box, makeStyles, Divider } from '@material-ui/core';

import {
    useSafeIntl,
    commonStyles,
    mapPopupStyles,
    IconButton,
} from 'bluesquare-components';

import MESSAGES from '../messages';
import { OrgUnit } from '../../orgUnits/types/orgUnit';
import { LinkToRegistry } from './LinkToRegistry';
import PopupItemComponent from '../../../components/maps/popups/PopupItemComponent';
import { LinkToOrgUnit } from '../../orgUnits/components/LinkToOrgUnit';

type Props = {
    orgUnit: OrgUnit;
};

const useStyles = makeStyles(theme => ({
    ...commonStyles(theme),
    ...mapPopupStyles(theme),
    popupCardContent: {
        ...mapPopupStyles(theme).popupCardContent,
        margin: theme.spacing(2),
    },
    popup: {
        ...mapPopupStyles(theme).popup,
        '& .leaflet-popup-content': {
            ...mapPopupStyles(theme).popup['& .leaflet-popup-content'],
            width: '300px !important',
        },
        '& a.leaflet-popup-close-button': {
            display: 'none',
        },
    },
}));

export const MapPopUp: FunctionComponent<Props> = ({ orgUnit }) => {
    const { formatMessage } = useSafeIntl();
    const classes: Record<string, string> = useStyles();
    const popup: any = useRef();

    return (
        <Popup className={classes.popup} ref={popup}>
            <Card className={classes.popupCard}>
                <Box display="flex" justifyContent="flex-end" px={1} py="4px">
                    <Box mr="auto">
                        <LinkToOrgUnit
                            orgUnit={orgUnit}
                            useIcon
                            iconSize="small"
                            size="small"
                        />
                        <LinkToRegistry
                            orgUnit={orgUnit}
                            replace
                            useIcon
                            iconSize="small"
                            size="small"
                        />
                    </Box>
                    <IconButton
                        onClick={() =>
                            popup.current.leafletElement.options.leaflet.map.closePopup()
                        }
                        icon="clear"
                        tooltipMessage={MESSAGES.close}
                        iconSize="small"
                        size="small"
                    />
                </Box>
                <Divider />
                <CardContent className={classes.popupCardContent}>
                    <PopupItemComponent
                        label={formatMessage(MESSAGES.name)}
                        value={orgUnit.name}
                    />
                    <PopupItemComponent
                        label={formatMessage(MESSAGES.type)}
                        value={orgUnit.org_unit_type_name}
                    />
                    <PopupItemComponent
                        label={formatMessage(MESSAGES.source)}
                        value={orgUnit.source}
                    />
                </CardContent>
            </Card>
        </Popup>
    );
};
