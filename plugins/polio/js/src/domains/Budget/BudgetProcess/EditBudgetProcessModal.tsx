import { Box, Divider, Grid, Typography } from '@mui/material';
import {
    Field,
    FormikErrors,
    FormikProvider,
    FormikTouched,
    useFormik,
} from 'formik';
import { isEqual } from 'lodash';
import React, { FunctionComponent, useCallback, useEffect } from 'react';

import {
    ConfirmCancelModal,
    ExpandableItem,
    LoadingSpinner,
    makeFullModal,
    useSafeIntl,
} from 'bluesquare-components';
import { EditIconButton } from '../../../../../../../hat/assets/js/apps/Iaso/components/Buttons/EditIconButton';

import { hasFormikFieldError } from '../../../../../../../hat/assets/js/apps/Iaso/utils/forms';
import { DateInput } from '../../../components/Inputs';
import { MultiSelect } from '../../../components/Inputs/MultiSelect';
import {
    BUDGET_REQUEST,
    BUDGET_STATES,
    ORPG_REVIEW,
    REVIEW_FOR_APPROVAL,
    RRT_REVIEW,
    WORKFLOW_SUFFIX,
} from '../../../constants/budget';
import { useEditBudgetProcess } from '../hooks/api/useEditBudgetProcess';
import { useGetBudget } from '../hooks/api/useGetBudget';
import { useAvailableRoundsForUpdate } from '../hooks/api/useGetBudgetProcessAvailableRounds';
import MESSAGES from '../messages';
import { Budget, BudgetDetail } from '../types';
import { formatRoundNumber } from '../utils';
import { useEditBudgetProcessSchema } from './validation';

type Props = {
    isOpen: boolean;
    closeDialog: () => void;
    budgetProcess: Budget;
};
const findErrorInFieldList = (
    keys: string[],
    errors: FormikErrors<any>,
    touched: FormikTouched<any>,
): boolean => {
    return Boolean(
        keys.find(key =>
            hasFormikFieldError(`${key}${WORKFLOW_SUFFIX}`, errors, touched),
        ),
    );
};
const findBudgetStateIndex = (values: Record<string, any>): number => {
    for (let i = BUDGET_STATES.length - 1; i >= 0; i -= 1) {
        const key = `${BUDGET_STATES[i]}${WORKFLOW_SUFFIX}`;
        if (values[key]) {
            return i;
        }
    }
    return -1;
};
const findNewBudgetState = (
    fieldIndex: number,
    values: Record<string, any>,
): string | null => {
    for (let i = fieldIndex - 1; i >= 0; i -= 1) {
        const key = `${BUDGET_STATES[i]}${WORKFLOW_SUFFIX}`;
        if (values[key]) {
            return BUDGET_STATES[i];
        }
    }
    return null;
};
const EditBudgetProcessModal: FunctionComponent<Props> = ({
    isOpen,
    closeDialog,
    budgetProcess,
}) => {
    const { formatMessage } = useSafeIntl();
    const { data: budget } = useGetBudget(budgetProcess.id);
    const { data: availableRounds, isFetching: isFetchingAvailableRounds } =
        useAvailableRoundsForUpdate(
            budgetProcess.campaign_id,
            budgetProcess.id,
        );

    const { mutate: confirm } = useEditBudgetProcess();
    const schema = useEditBudgetProcessSchema();
    const formik = useFormik<Partial<BudgetDetail>>({
        initialValues: {},
        enableReinitialize: true,
        validateOnBlur: true,
        validationSchema: schema,
        onSubmit: async newValues => {
            confirm({
                id: budgetProcess.id,
                ...newValues,
                rounds: newValues.rounds,
            });
        },
    });

    useEffect(() => {
        if (budget) {
            const newValues: BudgetDetail = {
                ...budget,
                rounds:
                    budget.rounds?.map(round => ({
                        ...round,
                        value: round.id,
                        label: formatRoundNumber(round.number),
                    })) || [],
            };
            if (!isEqual(formik.values, newValues)) {
                formik.setValues(newValues);
            }
        }
        // only change formik values while fetching budget detail
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [budget]);
    const { values, isSubmitting, isValid, errors, touched, setFieldValue } =
        formik;
    const isFormChanged = !isEqual(values, budget);
    const allowConfirm = !isSubmitting && isValid && isFormChanged;
    const updateBudgetStatus = useCallback(
        (fieldName: string, value: any) => {
            const fieldKey = fieldName.replace(WORKFLOW_SUFFIX, '');
            const computedBudgetStatusIndex = findBudgetStateIndex(values);
            const fieldIndex = BUDGET_STATES.findIndex(
                budgetState => budgetState === fieldKey,
            );
            if (fieldIndex > computedBudgetStatusIndex && value) {
                // setFieldValue('budget_status', fieldKey);
                setFieldValue('current_state_key', fieldKey);
            } else if (!value && fieldIndex >= computedBudgetStatusIndex) {
                const newBudgetState = findNewBudgetState(fieldIndex, values);
                // setFieldValue('budget_status', newBudgetState);
                setFieldValue('current_state_key', newBudgetState ?? '-');
            }
        },
        [setFieldValue, values],
    );
    const hasRequestFieldsError: boolean = findErrorInFieldList(
        BUDGET_REQUEST,
        errors,
        touched,
    );
    const hasRRTReviewError: boolean = findErrorInFieldList(
        RRT_REVIEW,
        errors,
        touched,
    );
    const hasORPGReviewError: boolean = findErrorInFieldList(
        ORPG_REVIEW,
        errors,
        touched,
    );
    const hasApprovalFieldsError: boolean = findErrorInFieldList(
        REVIEW_FOR_APPROVAL,
        errors,
        touched,
    );
    const disableEdition = budget?.has_data_in_budget_tool ?? false;
    return (
        <FormikProvider value={formik}>
            {isFetchingAvailableRounds && <LoadingSpinner />}
            {!isFetchingAvailableRounds && (
                <ConfirmCancelModal
                    open={isOpen}
                    closeDialog={closeDialog}
                    onClose={() => null}
                    id="edit-budget-process"
                    dataTestId="edit-budget-process"
                    titleMessage={MESSAGES.modalEditBudgetProcess}
                    onConfirm={() => formik.handleSubmit()}
                    onCancel={() => null}
                    confirmMessage={MESSAGES.modalWriteConfirm}
                    allowConfirm={allowConfirm}
                    cancelMessage={MESSAGES.modalWriteCancel}
                >
                    <Box mb={2}>
                        <Divider />
                    </Box>
                    <Box mb={2}>
                        <Field
                            label={formatMessage(MESSAGES.labelRound)}
                            name="rounds"
                            component={MultiSelect}
                            options={availableRounds}
                            returnFullObject
                        />
                    </Box>

                    <Grid container direction="row" item spacing={2}>
                        <Grid item>
                            <Box mb={2} px={2} py={2}>
                                <Typography variant="button">
                                    {`${formatMessage(MESSAGES.status)}: ${
                                        budget?.current_state?.label
                                    }`}
                                </Typography>
                            </Box>
                            <Box>
                                <Divider />
                            </Box>
                        </Grid>
                        <Grid item xs={12} lg={6}>
                            <ExpandableItem
                                label={formatMessage(MESSAGES.budgetRequest)}
                                preventCollapse={hasRequestFieldsError}
                            >
                                {BUDGET_REQUEST.map((node, index) => {
                                    return (
                                        <Box
                                            mt={index === 0 ? 2 : 0}
                                            key={node}
                                        >
                                            <Field
                                                label={formatMessage(
                                                    MESSAGES[node],
                                                )}
                                                name={`${node}${WORKFLOW_SUFFIX}`}
                                                component={DateInput}
                                                fullWidth
                                                disabled={disableEdition}
                                                onChange={updateBudgetStatus}
                                            />
                                        </Box>
                                    );
                                })}
                            </ExpandableItem>
                            <Divider style={{ height: '1px', width: '100%' }} />
                            <ExpandableItem
                                label={formatMessage(MESSAGES.RRTReview)}
                                preventCollapse={hasRRTReviewError}
                            >
                                {RRT_REVIEW.map((node, index) => {
                                    return (
                                        <Box
                                            mt={index === 0 ? 2 : 0}
                                            key={node}
                                        >
                                            <Field
                                                label={formatMessage(
                                                    MESSAGES[node],
                                                )}
                                                name={`${node}${WORKFLOW_SUFFIX}`}
                                                component={DateInput}
                                                fullWidth
                                                disabled={disableEdition}
                                                onChange={updateBudgetStatus}
                                            />
                                        </Box>
                                    );
                                })}
                            </ExpandableItem>
                            <Box mb={2}>
                                <Divider />
                            </Box>
                        </Grid>

                        <Grid item xs={12} lg={6}>
                            <ExpandableItem
                                label={formatMessage(MESSAGES.ORPGReview)}
                                preventCollapse={hasORPGReviewError}
                            >
                                {ORPG_REVIEW.map((node, index) => {
                                    return (
                                        <Box
                                            mt={index === 0 ? 2 : 0}
                                            key={node}
                                        >
                                            <Field
                                                label={formatMessage(
                                                    MESSAGES[node],
                                                )}
                                                name={`${node}${WORKFLOW_SUFFIX}`}
                                                component={DateInput}
                                                fullWidth
                                                disabled={disableEdition}
                                                onChange={updateBudgetStatus}
                                            />
                                        </Box>
                                    );
                                })}
                            </ExpandableItem>
                            <Box>
                                <Divider />
                            </Box>
                            <ExpandableItem
                                label={formatMessage(MESSAGES.approval)}
                                preventCollapse={hasApprovalFieldsError}
                            >
                                {REVIEW_FOR_APPROVAL.map((node, index) => {
                                    return (
                                        <Box
                                            mt={index === 0 ? 2 : 0}
                                            key={node}
                                        >
                                            <Field
                                                label={formatMessage(
                                                    MESSAGES[node],
                                                )}
                                                name={`${node}${WORKFLOW_SUFFIX}`}
                                                component={DateInput}
                                                fullWidth
                                                disabled={disableEdition}
                                                onChange={updateBudgetStatus}
                                            />
                                        </Box>
                                    );
                                })}
                            </ExpandableItem>
                            <Box mb={2}>
                                <Divider
                                    style={{ height: '1px', width: '100%' }}
                                />
                            </Box>
                        </Grid>
                    </Grid>
                </ConfirmCancelModal>
            )}
        </FormikProvider>
    );
};
const modalWithIcon = makeFullModal(EditBudgetProcessModal, EditIconButton);

export { modalWithIcon as EditBudgetProcessModal };
