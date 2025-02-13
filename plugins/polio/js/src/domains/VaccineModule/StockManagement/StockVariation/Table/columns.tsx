import EditIcon from '@mui/icons-material/Edit';
import { Column, textPlaceholder, useSafeIntl } from 'bluesquare-components';
import React, { useMemo } from 'react';
import { DateCell } from '../../../../../../../../../hat/assets/js/apps/Iaso/components/Cells/DateTimeCell';
import { NumberCell } from '../../../../../../../../../hat/assets/js/apps/Iaso/components/Cells/NumberCell';
import DeleteDialog from '../../../../../../../../../hat/assets/js/apps/Iaso/components/dialogs/DeleteDialogComponent';
import { PdfPreview } from '../../../../../../../../../hat/assets/js/apps/Iaso/components/files/pdf/PdfPreview';
import { STOCK_MANAGEMENT_WRITE } from '../../../../../constants/permissions';
import { VaccineForStock } from '../../../../../constants/types';
import MESSAGES from '../../messages';
import { EditDestruction } from '../Modals/CreateEditDestruction';
import { EditFormA } from '../Modals/CreateEditFormA';
import { EditIncident } from '../Modals/CreateEditIncident';

import { BreakWordCell } from '../../../../../../../../../hat/assets/js/apps/Iaso/components/Cells/BreakWordCell';
import { DisplayIfUserHasPerm } from '../../../../../../../../../hat/assets/js/apps/Iaso/components/DisplayIfUserHasPerm';
import { USED } from '../../constants';
import {
    useDeleteDestruction,
    useDeleteEarmarked,
    useDeleteFormA,
    useDeleteIncident,
} from '../../hooks/api';
import { EditEarmarked } from '../Modals/CreateEditEarmarked';

export const useFormATableColumns = (
    countryName: string,
    vaccine: VaccineForStock,
): Column[] => {
    const { formatMessage } = useSafeIntl();
    const { mutateAsync: deleteFormA } = useDeleteFormA();

    return useMemo(() => {
        const columns = [
            {
                Header: formatMessage(MESSAGES.campaign),
                accessor: 'campaign',
                id: 'campaign',
                sortable: true,
            },
            {
                Header: formatMessage(MESSAGES.round),
                accessor: 'round_number',
                id: 'round__number',
                sortable: true,
                Cell: settings =>
                    settings.row.original.round_number
                        ? settings.row.original.round_number
                        : textPlaceholder,
            },
            {
                Header: formatMessage(MESSAGES.form_a_reception_date),
                accessor: 'form_a_reception_date',
                id: 'form_a_reception_date',
                sortable: true,
                Cell: DateCell,
            },
            {
                Header: formatMessage(MESSAGES.report_date),
                accessor: 'report_date',
                id: 'report_date',
                sortable: true,
                Cell: DateCell,
            },
            {
                Header: formatMessage(MESSAGES.forma_vials_used),
                accessor: 'usable_vials_used',
                id: 'usable_vials_used',
                sortable: true,
                Cell: settings => (
                    <NumberCell
                        value={settings.row.original.usable_vials_used}
                    />
                ),
            },
            {
                Header: formatMessage(MESSAGES.forma_vials_missing),
                accessor: 'missing_vials',
                id: 'missing_vials',
                sortable: true,
                Cell: settings => {
                    if (settings.row.original.missing_vials) {
                        return (
                            <NumberCell
                                value={settings.row.original.missing_vials}
                            />
                        );
                    }
                    return textPlaceholder;
                },
            },
            {
                Header: formatMessage(MESSAGES.actions),
                id: 'account',
                accessor: 'account',
                sortable: false,
                Cell: settings => {
                    return (
                        <>
                            <PdfPreview
                                pdfUrl={settings.row.original.document}
                            />
                            <DisplayIfUserHasPerm
                                permissions={[STOCK_MANAGEMENT_WRITE]}
                            >
                                <>
                                    <EditFormA
                                        id={settings.row.original.id}
                                        formA={settings.row.original}
                                        iconProps={{ overrideIcon: EditIcon }}
                                        countryName={countryName}
                                        vaccine={vaccine}
                                        vaccineStockId={
                                            settings.row.original.vaccine_stock
                                        }
                                    />
                                    <DeleteDialog
                                        titleMessage={MESSAGES.deleteFormA}
                                        message={MESSAGES.deleteFormAWarning}
                                        onConfirm={() =>
                                            deleteFormA(
                                                settings.row.original.id,
                                            )
                                        }
                                    />
                                </>
                            </DisplayIfUserHasPerm>
                        </>
                    );
                },
            },
        ];
        return columns;
    }, [formatMessage, countryName, vaccine, deleteFormA]);
};
export const useDestructionTableColumns = (
    countryName: string,
    vaccine: VaccineForStock,
): Column[] => {
    const { formatMessage } = useSafeIntl();
    const { mutateAsync: deleteDestruction } = useDeleteDestruction();

    return useMemo(() => {
        const columns = [
            {
                Header: formatMessage(MESSAGES.title),
                accessor: 'action',
                id: 'action',
                sortable: true,
            },
            {
                Header: formatMessage(
                    MESSAGES.rrt_destruction_report_reception_date,
                ),
                accessor: 'rrt_destruction_report_reception_date',
                id: 'rrt_destruction_report_reception_date',
                sortable: true,
                Cell: DateCell,
            },
            {
                Header: formatMessage(MESSAGES.report_date),
                accessor: 'destruction_report_date',
                id: 'destruction_report_date',
                sortable: true,
                Cell: DateCell,
            },
            {
                Header: formatMessage(MESSAGES.vials_destroyed),
                accessor: 'unusable_vials_destroyed',
                id: 'unusable_vials_destroyed',
                sortable: true,
                Cell: settings => (
                    <NumberCell
                        value={settings.row.original.unusable_vials_destroyed}
                    />
                ),
            },
            {
                Header: formatMessage(MESSAGES.actions),
                accessor: 'account',
                id: 'account',
                sortable: false,
                Cell: settings => {
                    return (
                        <>
                            <PdfPreview
                                pdfUrl={settings.row.original.document}
                            />
                            <DisplayIfUserHasPerm
                                permissions={[STOCK_MANAGEMENT_WRITE]}
                            >
                                <>
                                    <EditDestruction
                                        id={settings.row.original.id}
                                        destruction={settings.row.original}
                                        iconProps={{ overrideIcon: EditIcon }}
                                        countryName={countryName}
                                        vaccine={vaccine}
                                        vaccineStockId={
                                            settings.row.original.vaccine_stock
                                        }
                                    />
                                    <DeleteDialog
                                        titleMessage={
                                            MESSAGES.deleteDestruction
                                        }
                                        message={
                                            MESSAGES.deleteDestructionWarning
                                        }
                                        onConfirm={() =>
                                            deleteDestruction(
                                                settings.row.original.id,
                                            )
                                        }
                                    />
                                </>
                            </DisplayIfUserHasPerm>
                        </>
                    );
                },
            },
        ];
        return columns;
    }, [countryName, formatMessage, vaccine, deleteDestruction]);
};
export const useIncidentTableColumns = (
    countryName: string,
    vaccine: VaccineForStock,
): Column[] => {
    const { formatMessage } = useSafeIntl();
    const { mutateAsync: deleteIncident } = useDeleteIncident();
    return useMemo(() => {
        const columns = [
            {
                Header: formatMessage(MESSAGES.stockCorrection),
                accessor: 'stock_correction',
                id: 'stock_correction',
                sortable: true,
                Cell: settings =>
                    settings.row.original.stock_correction
                        ? formatMessage(
                              MESSAGES[settings.row.original.stock_correction],
                          )
                        : textPlaceholder,
            },
            {
                Header: formatMessage(MESSAGES.title),
                accessor: 'title',
                id: 'title',
                sortable: true,
                Cell: BreakWordCell,
            },
            {
                Header: formatMessage(MESSAGES.incident_report_received_by_rrt),
                accessor: 'incident_report_received_by_rrt',
                id: 'incident_report_received_by_rrt',
                sortable: true,
                Cell: DateCell,
            },
            {
                Header: formatMessage(MESSAGES.report_date),
                accessor: 'date_of_incident_report',
                id: 'date_of_incident_report',
                sortable: true,
                Cell: DateCell,
            },
            {
                Header: formatMessage(MESSAGES.usable_vials),
                accessor: 'usable_vials',
                id: 'usable_vials',
                sortable: true,
                Cell: settings => (
                    <NumberCell value={settings.row.original.usable_vials} />
                ),
            },
            {
                Header: formatMessage(MESSAGES.unusable_vials),
                accessor: 'unusable_vials',
                id: 'unusable_vials',
                sortable: true,
                Cell: settings => (
                    <NumberCell value={settings.row.original.unusable_vials} />
                ),
            },
            {
                Header: formatMessage(MESSAGES.actions),
                accessor: 'account',
                id: 'account',
                sortable: false,
                Cell: settings => {
                    return (
                        <>
                            <PdfPreview
                                pdfUrl={settings.row.original.document}
                            />

                            <DisplayIfUserHasPerm
                                permissions={[STOCK_MANAGEMENT_WRITE]}
                            >
                                <>
                                    <EditIncident
                                        id={settings.row.original.id}
                                        incident={settings.row.original}
                                        iconProps={{ overrideIcon: EditIcon }}
                                        countryName={countryName}
                                        vaccine={vaccine}
                                        vaccineStockId={
                                            settings.row.original.vaccine_stock
                                        }
                                    />
                                    <DeleteDialog
                                        titleMessage={MESSAGES.deleteIncident}
                                        message={MESSAGES.deleteIncidentWarning}
                                        onConfirm={() =>
                                            deleteIncident(
                                                settings.row.original.id,
                                            )
                                        }
                                    />
                                </>
                            </DisplayIfUserHasPerm>
                        </>
                    );
                },
            },
        ];
        return columns;
    }, [countryName, formatMessage, vaccine, deleteIncident]);
};
export const useEarmarkedTableColumns = (
    countryName: string,
    vaccine: VaccineForStock,
): Column[] => {
    const { formatMessage } = useSafeIntl();
    const { mutateAsync: deleteEarmarked } = useDeleteEarmarked();
    return useMemo(() => {
        const columns = [
            {
                Header: formatMessage(MESSAGES.movement),
                accessor: 'earmarked_stock_type',
                id: 'earmarked_stock_type',
                sortable: true,
                Cell: settings => {
                    if (settings.row.original.earmarked_stock_type) {
                        if (
                            MESSAGES[settings.row.original.earmarked_stock_type]
                        ) {
                            return formatMessage(
                                MESSAGES[
                                    settings.row.original.earmarked_stock_type
                                ],
                            );
                        }
                        return settings.row.original.earmarked_stock_type;
                    }
                    return textPlaceholder;
                },
            },
            {
                Header: formatMessage(MESSAGES.campaign),
                accessor: 'campaign',
                id: 'campaign',
                sortable: true,
                Cell: BreakWordCell,
            },
            {
                Header: formatMessage(MESSAGES.round),
                accessor: 'round_number',
                id: 'round_number',
                sortable: true,
                Cell: settings => (
                    <NumberCell value={settings.row.original.round_number} />
                ),
            },
            {
                Header: formatMessage(MESSAGES.created),
                accessor: 'created_at',
                id: 'created_at',
                sortable: true,
                Cell: DateCell,
            },
            {
                Header: formatMessage(MESSAGES.earmarked_vials),
                accessor: 'vials_earmarked',
                id: 'vials_earmarked',
                sortable: true,
                Cell: settings => (
                    <NumberCell value={settings.row.original.vials_earmarked} />
                ),
            },
            {
                Header: formatMessage(MESSAGES.earmarked_doses),
                accessor: 'doses_earmarked',
                id: 'doses_earmarked',
                sortable: true,
                Cell: settings => (
                    <NumberCell value={settings.row.original.doses_earmarked} />
                ),
            },
            {
                Header: formatMessage(MESSAGES.actions),
                accessor: 'account',
                id: 'account',
                sortable: false,
                Cell: settings => {
                    if (settings.row.original.earmarked_stock_type === USED) {
                        return null;
                    }
                    return (
                        <DisplayIfUserHasPerm
                            permissions={[STOCK_MANAGEMENT_WRITE]}
                        >
                            <>
                                <EditEarmarked
                                    id={settings.row.original.id}
                                    earmark={settings.row.original}
                                    iconProps={{ overrideIcon: EditIcon }}
                                    countryName={countryName}
                                    vaccine={vaccine}
                                    vaccineStockId={
                                        settings.row.original.vaccine_stock
                                    }
                                />
                                <DeleteDialog
                                    titleMessage={MESSAGES.deleteEarmarked}
                                    message={MESSAGES.deleteEarmarkedWarning}
                                    onConfirm={() =>
                                        deleteEarmarked(
                                            settings.row.original.id,
                                        )
                                    }
                                />
                            </>
                        </DisplayIfUserHasPerm>
                    );
                },
            },
        ];
        return columns;
    }, [formatMessage, countryName, vaccine, deleteEarmarked]);
};
