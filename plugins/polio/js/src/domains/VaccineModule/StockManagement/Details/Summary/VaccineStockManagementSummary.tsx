import { Table, TableBody } from '@mui/material';
import { makeStyles } from '@mui/styles';
import { useSafeIntl } from 'bluesquare-components';
import classnames from 'classnames';
import React, { FunctionComponent } from 'react';
import WidgetPaper from '../../../../../../../../../hat/assets/js/apps/Iaso/components/papers/WidgetPaperComponent';
import { PaperTableRow } from '../../../../../../../../../hat/assets/js/apps/Iaso/components/tables/PaperTableRow';
import MESSAGES from '../../messages';
import { SummaryTitle } from './SummaryTitle';

const useStyles = makeStyles({
    paper: {
        '& .MuiTable-root': {
            width: '100%',
        },
    },
});

type Props = { isLoading: boolean; data: any };

export const VaccineStockManagementSummary: FunctionComponent<Props> = ({
    isLoading,
    data,
}) => {
    const classes: Record<string, string> = useStyles();
    const { formatMessage } = useSafeIntl();
    const isBopv = data?.vaccine_type === 'bOPV';

    return (
        <WidgetPaper
            className={classnames(classes.paper)}
            title={
                <SummaryTitle
                    title={formatMessage(MESSAGES.stockBalance)}
                    id={data?.country_id}
                />
            }
        >
            <Table size="small">
                <TableBody>
                    <PaperTableRow
                        label={formatMessage(MESSAGES.usableVials)}
                        value={data?.total_usable_vials}
                        isLoading={isLoading}
                    />
                    {!isBopv && (
                        <PaperTableRow
                            label={formatMessage(MESSAGES.unusableVials)}
                            value={data?.total_unusable_vials}
                            isLoading={isLoading}
                        />
                    )}
                    <PaperTableRow
                        label={formatMessage(MESSAGES.usableDoses)}
                        value={data?.total_usable_doses}
                        isLoading={isLoading}
                    />
                    {!isBopv && (
                        <PaperTableRow
                            label={formatMessage(MESSAGES.unusableDoses)}
                            value={data?.total_unusable_doses}
                            isLoading={isLoading}
                        />
                    )}
                    <PaperTableRow
                        label={formatMessage(MESSAGES.earmarked_vials)}
                        value={data?.total_earmarked_vials}
                        isLoading={isLoading}
                    />
                    <PaperTableRow
                        label={formatMessage(MESSAGES.earmarked_doses)}
                        value={data?.total_earmarked_doses}
                        isLoading={isLoading}
                    />
                </TableBody>
            </Table>
        </WidgetPaper>
    );
};
