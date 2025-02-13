import { Column, textPlaceholder, useSafeIntl } from 'bluesquare-components';
import React, { useMemo } from 'react';
import { DateCell } from '../../../../../../../../../hat/assets/js/apps/Iaso/components/Cells/DateTimeCell';
import { NumberCell } from '../../../../../../../../../hat/assets/js/apps/Iaso/components/Cells/NumberCell';
import MESSAGES from '../../messages';

export const useVaccineStockManagementDetailsColumnsUsable = (): Column[] => {
    const { formatMessage } = useSafeIntl();
    return useMemo(() => {
        const columns = [
            {
                Header: formatMessage(MESSAGES.date),
                accessor: 'date',
                id: 'date',
                Cell: DateCell,
            },
            {
                Header: formatMessage(MESSAGES.action),
                accessor: 'action',
                id: 'action',
                Cell: settings => {
                    const { action } = settings.row.original;
                    return MESSAGES[action]
                        ? formatMessage(MESSAGES[action])
                        : action;
                },
            },
            {
                Header: formatMessage(MESSAGES.vials_in),
                accessor: 'vials_in',
                Cell: settings => {
                    const { vials_in } = settings.row.original;
                    if (!vials_in) {
                        return <span>{textPlaceholder}</span>;
                    }
                    return <NumberCell value={vials_in} />;
                },
            },
            {
                Header: formatMessage(MESSAGES.vials_out),
                accessor: 'vials_out',
                Cell: settings => {
                    const { vials_out } = settings.row.original;
                    if (!vials_out) {
                        return <span>{textPlaceholder}</span>;
                    }

                    return <NumberCell value={vials_out} />;
                },
            },
            {
                Header: formatMessage(MESSAGES.doses_in),
                accessor: 'doses_in',
                Cell: settings => {
                    const { doses_in } = settings.row.original;
                    if (!doses_in) {
                        return <span>{textPlaceholder}</span>;
                    }

                    return <NumberCell value={doses_in} />;
                },
            },
            {
                Header: formatMessage(MESSAGES.doses_out),
                accessor: 'doses_out',
                Cell: settings => {
                    const { doses_out } = settings.row.original;
                    if (!doses_out) {
                        return <span>{textPlaceholder}</span>;
                    }

                    return <NumberCell value={doses_out} />;
                },
            },
        ];
        return columns;
    }, [formatMessage]);
};

export const useVaccineStockManagementDetailsColumnsUnusable = (): Column[] => {
    const { formatMessage } = useSafeIntl();
    return useMemo(() => {
        const columns = [
            {
                Header: formatMessage(MESSAGES.date),
                accessor: 'date',
                id: 'date',
                Cell: DateCell,
            },
            {
                Header: formatMessage(MESSAGES.action),
                accessor: 'action',
                id: 'action',
                Cell: settings => {
                    const { action } = settings.row.original;
                    return MESSAGES[action]
                        ? formatMessage(MESSAGES[action])
                        : action;
                },
            },
            {
                Header: formatMessage(MESSAGES.vials_in),
                accessor: 'vials_in',
                Cell: settings => {
                    const { vials_in } = settings.row.original;
                    if (!vials_in) {
                        return <span>{textPlaceholder}</span>;
                    }
                    return <NumberCell value={vials_in} />;
                },
            },
            {
                Header: formatMessage(MESSAGES.vials_out),
                accessor: 'vials_out',
                Cell: settings => {
                    const { vials_out } = settings.row.original;
                    if (!vials_out) {
                        return <span>{textPlaceholder}</span>;
                    }

                    return <NumberCell value={vials_out} />;
                },
            },
        ];
        return columns;
    }, [formatMessage]);
};
export const useVaccineStockManagementDetailsColumnsEarmarked =
    (): Column[] => {
        const { formatMessage } = useSafeIntl();
        return useMemo(() => {
            const columns = [
                {
                    Header: formatMessage(MESSAGES.date),
                    accessor: 'date',
                    id: 'date',
                    Cell: DateCell,
                },
                {
                    Header: formatMessage(MESSAGES.action),
                    accessor: 'action',
                    id: 'action',
                    Cell: settings => {
                        const { action } = settings.row.original;
                        return MESSAGES[action]
                            ? formatMessage(MESSAGES[action])
                            : action;
                    },
                },
                {
                    Header: formatMessage(MESSAGES.vials_in),
                    accessor: 'vials_in',
                    Cell: settings => {
                        const { vials_in } = settings.row.original;
                        if (!vials_in) {
                            return <span>{textPlaceholder}</span>;
                        }
                        return <NumberCell value={vials_in} />;
                    },
                },
                {
                    Header: formatMessage(MESSAGES.vials_out),
                    accessor: 'vials_out',
                    Cell: settings => {
                        const { vials_out } = settings.row.original;
                        if (!vials_out) {
                            return <span>{textPlaceholder}</span>;
                        }

                        return <NumberCell value={vials_out} />;
                    },
                },
            ];
            return columns;
        }, [formatMessage]);
    };
