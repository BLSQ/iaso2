import { Box } from '@mui/material';
import {
    AddButton,
    ConfirmCancelModal,
    makeFullModal,
    useSafeIntl,
} from 'bluesquare-components';
import { Field, FormikProvider, useFormik } from 'formik';
import { isEqual } from 'lodash';
import React, { FunctionComponent } from 'react';
import { EditIconButton } from '../../../../../../../../../hat/assets/js/apps/Iaso/components/Buttons/EditIconButton';
import {
    DateInput,
    NumberInput,
    TextInput,
} from '../../../../../components/Inputs';
import { SingleSelect } from '../../../../../components/Inputs/SingleSelect';
import { Vaccine } from '../../../../../constants/types';
import { useSaveIncident } from '../../hooks/api';
import MESSAGES from '../../messages';
import { useIncidentOptions } from './useIncidentOptions';
import { useIncidentValidation } from './validation';

type Props = {
    incident?: any;
    id?: number;
    isOpen: boolean;
    closeDialog: () => void;
    countryName: string;
    vaccine: Vaccine;
    vaccineStockId: string;
};

export const CreateEditIncident: FunctionComponent<Props> = ({
    incident,
    isOpen,
    closeDialog,
    countryName,
    vaccine,
    vaccineStockId,
}) => {
    const { formatMessage } = useSafeIntl();
    const { mutateAsync: save } = useSaveIncident();
    const validationSchema = useIncidentValidation();
    const formik = useFormik<any>({
        initialValues: {
            id: incident?.id,
            stock_correction: incident?.stock_correction,
            title: incident?.title,
            comment: incident?.comment,
            incident_report_received_by_rrt:
                incident?.incident_report_received_by_rrt,
            date_of_incident_report: incident?.date_of_incident_report,
            usable_vials: incident?.usable_vials,
            unusable_vials: incident?.unusable_vials,
            vaccine_stock: vaccineStockId,
        },
        onSubmit: values => save(values),
        validationSchema,
    });
    const incidentTypeOptions = useIncidentOptions();
    const titleMessage = incident?.id ? MESSAGES.edit : MESSAGES.create;
    const title = `${countryName} - ${vaccine}: ${formatMessage(
        titleMessage,
    )} ${formatMessage(MESSAGES.incidentReports)}`;
    const allowConfirm = formik.isValid && !isEqual(formik.touched, {});

    return (
        <FormikProvider value={formik}>
            <ConfirmCancelModal
                titleMessage={title}
                onConfirm={() => formik.handleSubmit()}
                allowConfirm={allowConfirm}
                open={isOpen}
                closeDialog={closeDialog}
                id="formA-modal"
                dataTestId="formA-modal"
                onCancel={() => null}
                onClose={() => {
                    closeDialog();
                }}
                confirmMessage={MESSAGES.save}
                cancelMessage={MESSAGES.cancel}
            >
                <Box mb={2}>
                    <Field
                        label={formatMessage(MESSAGES.stockCorrection)}
                        name="stock_correction"
                        component={SingleSelect}
                        required
                        options={incidentTypeOptions}
                        withMarginTop
                    />
                </Box>

                <Box mb={2}>
                    <Field
                        label={formatMessage(MESSAGES.title)}
                        name="title"
                        component={TextInput}
                        required
                        shrinkLabel={false}
                    />
                </Box>
                <Box mb={2} />
                <Field
                    label={formatMessage(
                        MESSAGES.incident_report_received_by_rrt,
                    )}
                    name="incident_report_received_by_rrt"
                    component={DateInput}
                    required
                />
                <Field
                    label={formatMessage(MESSAGES.report_date)}
                    name="date_of_incident_report"
                    component={DateInput}
                    required
                />
                <Box mb={2}>
                    <Field
                        label={formatMessage(MESSAGES.usable_vials)}
                        name="usable_vials"
                        component={NumberInput}
                        required
                    />
                </Box>
                <Box mb={2}>
                    <Field
                        label={formatMessage(MESSAGES.unusable_vials)}
                        name="unusable_vials"
                        component={NumberInput}
                        required
                    />
                </Box>
                <Field
                    label={formatMessage(MESSAGES.comment)}
                    name="comment"
                    multiline
                    component={TextInput}
                    shrinkLabel={false}
                />
            </ConfirmCancelModal>
        </FormikProvider>
    );
};
const modalWithButton = makeFullModal(CreateEditIncident, AddButton);
const modalWithIcon = makeFullModal(CreateEditIncident, EditIconButton);

export { modalWithButton as CreateIncident, modalWithIcon as EditIncident };
