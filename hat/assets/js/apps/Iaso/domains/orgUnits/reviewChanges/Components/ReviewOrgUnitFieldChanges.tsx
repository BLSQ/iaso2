import React, { FunctionComponent } from 'react';
import { Table, TableBody, TableCell, TableRow } from '@mui/material';
import { useSafeIntl } from 'bluesquare-components';
import { Accordion } from '../../../../components/Accordion/Accordion';
import { AccordionDetails } from '../../../../components/Accordion/AccordionDetails';
import { AccordionSummary } from '../../../../components/Accordion/AccordionSummary';
import { NewOrgUnitField } from '../hooks/useNewFields';
import MESSAGES from '../messages';
import { ExtendedNestedGroup, OrgUnitChangeRequestDetails } from '../types';

type Props = {
    fieldValues: ExtendedNestedGroup[];
    changeRequest?: OrgUnitChangeRequestDetails;
    field: NewOrgUnitField;
};

export const ReviewOrgUnitFieldChanges: FunctionComponent<Props> = ({
    fieldValues,
    changeRequest,
    field,
}) => {
    const { formatMessage } = useSafeIntl();
    const { status } = changeRequest || {};
    const isCellApproved =
        (status &&
            status === 'approved' &&
            changeRequest?.approved_fields.includes(`new_${field.key}`) &&
            'success.light') ||
        '';
    const isSelected =
        (status && field?.isSelected === true && 'success.light') || '';

    return (
        <Accordion defaultExpanded>
            <AccordionSummary
                aria-controls="change-request"
                id="change-request"
            >
                {formatMessage(MESSAGES.viewDetails)}
            </AccordionSummary>
            <AccordionDetails>
                <Table size="small">
                    <TableBody>
                        {fieldValues.map(value => {
                            const { name } = value;
                            const isHighlighted =
                                (((value.left === false &&
                                    value.right === true) ||
                                    (value.left === true &&
                                        value.right === false)) &&
                                    'error.light') ||
                                '';
                            return (
                                <TableRow key={value.id}>
                                    <TableCell
                                        sx={{
                                            width: '50%',
                                            borderBottom: 'none',
                                            color: isHighlighted,
                                        }}
                                    >
                                        {(value.left === true && name) || '--'}
                                    </TableCell>
                                    <TableCell
                                        sx={{
                                            width: '50%',
                                            borderBottom: 'none',
                                            color:
                                                isCellApproved ||
                                                isSelected ||
                                                isHighlighted,
                                        }}
                                    >
                                        {(value.right === true && name) || '--'}
                                    </TableCell>
                                </TableRow>
                            );
                        })}
                    </TableBody>
                </Table>
            </AccordionDetails>
        </Accordion>
    );
};
