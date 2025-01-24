import { Box } from '@mui/material';
import {
    AddButton,
    ConfirmCancelModal,
    makeFullModal,
    useSafeIntl,
} from 'bluesquare-components';
import { Field, FormikProvider, useFormik } from 'formik';
import { isEqual } from 'lodash';
import React, { FunctionComponent, useCallback } from 'react';
import { EditIconButton } from '../../../../../../../../../hat/assets/js/apps/Iaso/components/Buttons/EditIconButton';
import { NumberInput, TextInput } from '../../../../../components/Inputs';
import { SingleSelect } from '../../../../../components/Inputs/SingleSelect';
import { VaccineForStock } from '../../../../../constants/types';
import { dosesPerVial } from '../../../SupplyChain/hooks/utils';
import { useCampaignOptions, useSaveEarmarked } from '../../hooks/api';
import MESSAGES from '../../messages';
import { useEarmarkOptions } from './dropdownOptions';
import { useEarmarkValidation } from './validation';

type Props = {
    earmark?: any;
    id?: number;
    isOpen: boolean;
    closeDialog: () => void;
    countryName: string;
    vaccine: VaccineForStock;
    vaccineStockId: string;
};

export const CreateEditEarmarked: FunctionComponent<Props> = ({
    earmark,
    isOpen,
    closeDialog,
    countryName,
    vaccine,
    vaccineStockId,
}) => {
    const { formatMessage } = useSafeIntl();
    const { mutateAsync: save } = useSaveEarmarked();
    const validationSchema = useEarmarkValidation();
    const formik = useFormik<any>({
        initialValues: {
            id: earmark?.id,
            earmarked_stock_type: earmark?.earmarked_stock_type,
            campaign: earmark?.campaign,
            round_number: earmark?.round_number,
            comment: earmark?.comment,
            vials_earmarked: earmark?.vials_earmarked || 0,
            doses_earmarked: earmark?.doses_earmarked || 0,
            vaccine_stock: vaccineStockId,
        },
        onSubmit: values => save(values),
        validationSchema,
    });
    const { setFieldValue, setFieldTouched } = formik;

    const { campaignOptions, isFetching, roundNumberOptions } =
        useCampaignOptions(countryName, formik.values.campaign);

    const earmarkTypeOptions = useEarmarkOptions();

    const handleVialsChange = useCallback(
        value => {
            const conversionRate = dosesPerVial[vaccine];
            setFieldValue('vials_earmarked', value);
            setFieldValue('doses_earmarked', value * conversionRate);
            setFieldTouched('vials_earmarked', true);
        },
        [setFieldTouched, setFieldValue, vaccine],
    );

    const titleMessage = earmark?.id ? MESSAGES.edit : MESSAGES.create;
    const title = `${countryName} - ${vaccine}: ${formatMessage(
        titleMessage,
    )} ${formatMessage(MESSAGES.earmarked)}`;
    const allowConfirm = formik.isValid && !isEqual(formik.touched, {});

    return (
        <FormikProvider value={formik}>
            <ConfirmCancelModal
                titleMessage={title}
                onConfirm={() => formik.handleSubmit()}
                allowConfirm={allowConfirm}
                open={isOpen}
                closeDialog={closeDialog}
                id="earmarked-modal"
                dataTestId="earmarked-modal"
                onCancel={() => null}
                onClose={() => {
                    closeDialog();
                }}
                confirmMessage={MESSAGES.save}
                cancelMessage={MESSAGES.cancel}
            >
                <Box mb={2}>
                    <Field
                        label={formatMessage(MESSAGES.movement)}
                        name="earmarked_stock_type"
                        component={SingleSelect}
                        required
                        options={earmarkTypeOptions}
                        withMarginTop
                    />
                </Box>
                <Box mb={2}>
                    <Field
                        label={formatMessage(MESSAGES.campaign)}
                        name="campaign"
                        component={SingleSelect}
                        required
                        options={campaignOptions}
                        withMarginTop
                        isLoading={isFetching}
                        disabled={!countryName}
                    />
                </Box>
                <Box mb={2}>
                    <Field
                        label={formatMessage(MESSAGES.round)}
                        name="round_number"
                        component={SingleSelect}
                        required
                        options={roundNumberOptions}
                        withMarginTop
                        isLoading={isFetching}
                        disabled={!formik.values.campaign}
                    />
                </Box>
                <Box mb={2}>
                    <Field
                        label={formatMessage(MESSAGES.earmarked_vials)}
                        name="vials_earmarked"
                        component={NumberInput}
                        onChange={handleVialsChange}
                        required
                    />
                </Box>
                <Box mb={2}>
                    <Field
                        label={formatMessage(MESSAGES.comment)}
                        name="comment"
                        multiline
                        component={TextInput}
                        shrinkLabel={false}
                    />
                </Box>
            </ConfirmCancelModal>
        </FormikProvider>
    );
};
const modalWithButton = makeFullModal(CreateEditEarmarked, AddButton);
const modalWithIcon = makeFullModal(CreateEditEarmarked, EditIconButton);

export { modalWithButton as CreateEarmarked, modalWithIcon as EditEarmarked };
