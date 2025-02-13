import {
    Box,
    FormControl,
    FormControlLabel,
    FormLabel,
    Radio,
    RadioGroup,
    Typography,
} from '@mui/material';
import {
    AddButton,
    ConfirmCancelModal,
    makeFullModal,
    useSafeIntl,
} from 'bluesquare-components';
import { Field, FormikProvider, useFormik } from 'formik';
import { isEqual } from 'lodash';
import React, { FunctionComponent, useCallback, useMemo } from 'react';
import { EditIconButton } from '../../../../../../../../../hat/assets/js/apps/Iaso/components/Buttons/EditIconButton';
import DocumentUploadWithPreview from '../../../../../../../../../hat/assets/js/apps/Iaso/components/files/pdf/DocumentUploadWithPreview';
import { processErrorDocsBase } from '../../../../../../../../../hat/assets/js/apps/Iaso/components/files/pdf/utils';
import {
    DateInput,
    NumberInput,
    TextInput,
} from '../../../../../components/Inputs';
import { SingleSelect } from '../../../../../components/Inputs/SingleSelect';
import { Vaccine } from '../../../../../constants/types';
import { useSaveIncident } from '../../hooks/api';
import { useGetMovementDescription } from '../../hooks/useGetMovementDescription';
import MESSAGES from '../../messages';
import { useIncidentOptions } from './dropdownOptions';
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

/**
 * Incident Report Movement Types Documentation
 *
 * This module handles different types of vaccine stock movements for incident reports.
 * There are four main types of movements, each with its own behavior:
 *
 * 1. plainMovement:
 *    - Used for: vaccine_expired, unreadable_label, vvm_reached_discard_point
 *    - Behavior: Vials are still present but change from usable to unusable
 *    - Effect:
 *      * Decreases usable vials
 *      * Increases unusable vials
 *      * Total vial count remains the same
 *    - Example: 100 vials expire
 *      * usable_vials: 100
 *      * unusable_vials: +100
 *
 * 2. missingMovement:
 *    - Used for: broken, stealing, return, losses
 *    - Behavior: Vials are no longer present in the inventory
 *    - Effect:
 *      * Decreases usable vials
 *      * Unusable vials remain unchanged
 *      * Total vial count decreases
 *    - Example: 50 vials are stolen
 *      * usable_vials: 50
 *      * unusable_vials: 0
 *
 * 3. inventory:
 *    - Used for: physical_inventory
 *    - Behavior: Adjusts the count of either usable or unusable vials in based on physical inventory
 *    - Effect:
 *      * User chooses between usable or unusable vials
 *      * The chosen type (usable or unusable) can be increased or decreased
 *      * The other type is automatically set to zero
 *      * Total vial count may increase or decrease
 *    - Example 1: Physical count shows 20 more usable vials than recorded
 *      * usable_vials: 20
 *      * unusable_vials: 0
 *    - Example 2: Physical count shows 10 fewer unusable vials than recorded
 *      * usable_vials: 0
 *      * unusable_vials: 10
 *
 * Note: The actual addition or subtraction of vials is handled by the backend.
 * This frontend component is responsible for correctly categorizing the movement,
 * allowing the user to choose between usable and unusable vials for inventory movements,
 * and sending the appropriate values to the API.
 */
export type IncidentReportFieldType =
    | 'plainMovement'
    | 'missingMovement'
    | 'inOutMovement'
    | 'inventoryAdd'
    | 'inventoryRemove';
type IncidentReportConfig = {
    [key: string]: IncidentReportFieldType;
};

const makeIncidentReportConfig = (
    vaccineType: string,
): IncidentReportConfig => ({
    broken: vaccineType === 'bOPV' ? 'plainMovement' : 'inOutMovement',
    stealing: 'missingMovement',
    return: 'missingMovement',
    losses: 'missingMovement',
    vaccine_expired: 'plainMovement',
    unreadable_label: 'plainMovement',
    vvm_reached_discard_point: 'plainMovement',
    physical_inventory_add: 'inventoryAdd',
    physical_inventory_remove: 'inventoryRemove',
});

const getMovementLabel = (movementType: IncidentReportFieldType) => {
    switch (movementType) {
        case 'plainMovement':
        case 'missingMovement':
            return MESSAGES.vialsOut;
        default:
            return MESSAGES.movement;
    }
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
    const getMovementDescription = useGetMovementDescription();

    const [inventoryType, setInventoryType] = React.useState(() => {
        if (incident && incident.stock_correction === 'physical_inventory') {
            return incident.usable_vials > 0 ? 'usable' : 'unusable';
        }
        return 'usable';
    });
    const incidentConfig = useMemo(() => {
        return makeIncidentReportConfig(vaccine);
    }, [vaccine]);

    const getInitialMovement = useCallback(
        i => {
            if (!i) return 0;
            const movementType = incidentConfig[i.stock_correction];
            return movementType === 'inventoryAdd' ? 0 : i.usable_vials;
        },
        [incidentConfig],
    );

    const handleInventoryTypeChange = (
        event: React.ChangeEvent<HTMLInputElement>,
    ) => {
        setInventoryType(event.target.value);
        formik.setFieldValue(
            event.target.value === 'usable' ? 'unusable_vials' : 'usable_vials',
            0,
        );
    };

    const handleSubmit = useCallback(
        (values: any) => {
            const movementType = incidentConfig[values.stock_correction];
            const { movement } = values;

            let usableVials = 0;
            let unusableVials = 0;

            switch (movementType) {
                case 'plainMovement':
                    usableVials = movement;
                    unusableVials = movement;
                    break;
                case 'missingMovement':
                    usableVials = movement;
                    break;
                case 'inOutMovement':
                    usableVials = values.usable_vials;
                    unusableVials = values.unusable_vials;
                    break;
                case 'inventoryRemove':
                case 'inventoryAdd':
                    usableVials =
                        inventoryType === 'usable' ? values.usable_vials : 0;
                    unusableVials =
                        inventoryType === 'unusable'
                            ? values.unusable_vials
                            : 0;
                    break;
                default:
                    break;
            }

            const submissionValues = {
                ...values,
                usable_vials: usableVials,
                unusable_vials: unusableVials,
            };
            save(submissionValues);
        },
        [incidentConfig, inventoryType, save],
    );
    const formik = useFormik<any>({
        initialValues: {
            id: incident?.id,
            stock_correction: incident?.stock_correction,
            title: incident?.title,
            comment: incident?.comment,
            incident_report_received_by_rrt:
                incident?.incident_report_received_by_rrt,
            date_of_incident_report: incident?.date_of_incident_report,
            usable_vials: incident?.usable_vials || 0,
            unusable_vials: incident?.unusable_vials || 0,
            movement: getInitialMovement(incident),
            vaccine_stock: vaccineStockId,
            document: incident?.document,
        },
        onSubmit: handleSubmit,
        validationSchema,
    });

    const documentErrors = useMemo(() => {
        return processErrorDocsBase(formik.errors.document);
    }, [formik.errors.document]);

    const incidentTypeOptions = useIncidentOptions();
    const titleMessage = incident?.id ? MESSAGES.edit : MESSAGES.create;
    const title = `${countryName} - ${vaccine}: ${formatMessage(
        titleMessage,
    )} ${formatMessage(MESSAGES.incidentReports)}`;
    const allowConfirm = formik.isValid && !isEqual(formik.touched, {});

    const currentMovementType = incidentConfig[formik.values.stock_correction];

    return (
        <FormikProvider value={formik}>
            <ConfirmCancelModal
                titleMessage={title}
                onConfirm={() => formik.handleSubmit()}
                allowConfirm={allowConfirm}
                open={isOpen}
                closeDialog={closeDialog}
                id="incident-modal"
                dataTestId="incident-modal"
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

                {currentMovementType &&
                    currentMovementType !== 'inventoryAdd' &&
                    currentMovementType !== 'inventoryRemove' &&
                    currentMovementType !== 'inOutMovement' && (
                        <Box mb={2}>
                            <Field
                                label={formatMessage(
                                    getMovementLabel(currentMovementType),
                                )}
                                name="movement"
                                component={NumberInput}
                                required
                            />
                            <Typography variant="body2">
                                {getMovementDescription(
                                    currentMovementType,
                                    formik.values.movement,
                                )}
                            </Typography>
                        </Box>
                    )}
                {currentMovementType === 'inOutMovement' && (
                    <>
                        <Box mb={2}>
                            <Field
                                label={formatMessage(MESSAGES.usableVials)}
                                name="usable_vials"
                                component={NumberInput}
                                required
                            />
                            <Typography variant="body2">
                                {getMovementDescription(
                                    currentMovementType,
                                    formik.values.movement,
                                )}
                            </Typography>
                        </Box>
                        <Box mb={2}>
                            <Field
                                label={formatMessage(MESSAGES.unusableVials)}
                                name="unusable_vials"
                                component={NumberInput}
                                required
                            />
                            <Typography variant="body2">
                                {getMovementDescription(
                                    currentMovementType,
                                    formik.values.movement,
                                )}
                            </Typography>
                        </Box>
                    </>
                )}
                {(currentMovementType === 'inventoryAdd' ||
                    currentMovementType === 'inventoryRemove') && (
                    <>
                        <Box mb={2}>
                            <FormControl component="fieldset">
                                <FormLabel id="stock-type-choice-label">
                                    {formatMessage(MESSAGES.stockToModify)}
                                </FormLabel>
                                <RadioGroup
                                    aria-label="inventory type"
                                    name="inventoryType"
                                    value={inventoryType}
                                    onChange={handleInventoryTypeChange}
                                >
                                    <FormControlLabel
                                        value="usable"
                                        control={<Radio />}
                                        label={formatMessage(
                                            MESSAGES.usableVials,
                                        )}
                                    />
                                    <FormControlLabel
                                        value="unusable"
                                        control={<Radio />}
                                        label={formatMessage(
                                            MESSAGES.unusableVials,
                                        )}
                                    />
                                </RadioGroup>
                            </FormControl>
                        </Box>
                        <Box mb={2}>
                            <Field
                                label={formatMessage(
                                    inventoryType === 'usable'
                                        ? MESSAGES.usableVials
                                        : MESSAGES.unusableVials,
                                )}
                                name={
                                    inventoryType === 'usable'
                                        ? 'usable_vials'
                                        : 'unusable_vials'
                                }
                                component={NumberInput}
                                required
                            />
                        </Box>
                    </>
                )}
                <Box mb={2}>
                    <Field
                        label={formatMessage(MESSAGES.comment)}
                        name="comment"
                        multiline
                        component={TextInput}
                        shrinkLabel={false}
                    />
                </Box>
                <Box mb={2}>
                    <DocumentUploadWithPreview
                        errors={documentErrors}
                        onFilesSelect={files => {
                            if (files.length) {
                                formik.setFieldTouched('document', true);
                                formik.setFieldValue('document', files);
                            }
                        }}
                        document={formik.values.document}
                    />
                </Box>
            </ConfirmCancelModal>
        </FormikProvider>
    );
};
const modalWithButton = makeFullModal(CreateEditIncident, AddButton);
const modalWithIcon = makeFullModal(CreateEditIncident, EditIconButton);

export { modalWithButton as CreateIncident, modalWithIcon as EditIncident };
