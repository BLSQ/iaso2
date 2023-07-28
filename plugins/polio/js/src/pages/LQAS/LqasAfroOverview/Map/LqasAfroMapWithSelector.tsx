import React, { FunctionComponent } from 'react';
import {
    Box,
    Grid,
    Paper,
    FormControlLabel,
    Radio,
    RadioGroup,
} from '@material-ui/core';
import { paperElevation } from '../../../IM/constants';
import InputComponent from '../../../../../../../../hat/assets/js/apps/Iaso/components/forms/InputComponent';
import { LqasAfroMap } from './LqasAfroMap';
import { useOptions } from '../utils';
import { Router } from '../../../../../../../../hat/assets/js/apps/Iaso/types/general';
import { Tile } from '../../../../../../../../hat/assets/js/apps/Iaso/components/maps/tools/TilesSwitchControl';
import MESSAGES from '../../../../constants/messages';
import { AfroMapParams, Side } from '../types';

type Props = {
    selectedRound: string;
    // eslint-disable-next-line no-unused-vars
    onRoundChange: (value: string, side: Side) => void;
    router: Router;
    currentTile: Tile;
    setCurrentTile: React.Dispatch<React.SetStateAction<Tile>>;
    side: Side;
    params: AfroMapParams;
    // eslint-disable-next-line no-unused-vars
    onDisplayedShapeChange: (value: string, side: Side) => void;
};

export const LqasAfroMapWithSelector: FunctionComponent<Props> = ({
    selectedRound,
    onRoundChange,
    router,
    currentTile,
    setCurrentTile,
    side,
    params,
    onDisplayedShapeChange,
}) => {
    const options = useOptions();
    const shapeKey =
        side === 'left' ? 'displayedShapesLeft' : 'displayedShapesRight';

    return (
        <Paper elevation={paperElevation}>
            <Box px={2}>
                <Grid container spacing={4}>
                    <Grid item xs={6}>
                        <InputComponent
                            type="select"
                            multi={false}
                            keyValue="round"
                            onChange={(_, value) => onRoundChange(value, side)}
                            value={selectedRound}
                            options={options}
                            clearable={false}
                            label={MESSAGES.round}
                        />
                    </Grid>
                    <Grid item xs={6}>
                        <Box mt={3}>
                            <RadioGroup
                                row
                                name="displayedShapes"
                                value={params[shapeKey] || 'country'}
                                onChange={(_, value) =>
                                    onDisplayedShapeChange(value, side)
                                }
                            >
                                <FormControlLabel
                                    value="country"
                                    control={<Radio color="primary" />}
                                    label="COUNTRY"
                                />
                                <FormControlLabel
                                    value="district"
                                    control={<Radio color="primary" />}
                                    label="DISTRICT"
                                />
                            </RadioGroup>
                        </Box>
                    </Grid>
                </Grid>
            </Box>
            <Box m={2} pb={2}>
                <LqasAfroMap
                    router={router}
                    currentTile={currentTile}
                    setCurrentTile={setCurrentTile}
                    side={side}
                />
            </Box>
        </Paper>
    );
};
