import * as yup from 'yup';
import { useSafeIntl } from 'bluesquare-components';
import moment from 'moment';
import { useMemo } from 'react';
import { dateFormat } from '../../../Calendar/campaignCalendar/constants';
import MESSAGES from '../messages';

const dateKeys = {
    round: { start: 'start_date', end: 'end_date' },
    lqas: { start: 'lqas_started_at', end: 'lqas_ended_at' },
    im: { start: 'im_started_at', end: 'im_ended_at' },
};

yup.addMethod(
    yup.date,
    'validateStartDate',
    function validateStartDate(formatMessage, dateType = 'round') {
        return this.test('validateStartDate', '', (value, context) => {
            const keys = dateKeys[dateType];
            const { path, createError, parent } = context;
            const newStartDate = moment(value);
            const endDate =
                parent[keys.end] && moment(parent[keys.end], dateFormat);

            let errorMessage;

            if (endDate?.isBefore(newStartDate)) {
                errorMessage = formatMessage(MESSAGES.startDateAfterEndDate);
            }

            if (errorMessage) {
                return createError({
                    path,
                    message: errorMessage,
                });
            }
            return true;
        });
    },
);

yup.addMethod(
    yup.date,
    'validateLqasImStartDate',
    function validateLqasImStartDate(formatMessage) {
        return this.test('validateLqasImStartDate', '', (value, context) => {
            const keys = dateKeys.round;
            const { path, createError, parent } = context;
            if (!value) {
                return true;
            }
            const newStartDate = moment(value);
            const roundEndDate =
                parent[keys.end] && moment(parent[keys.end], dateFormat);

            let errorMessage;

            if (roundEndDate?.isAfter(newStartDate)) {
                errorMessage = formatMessage(MESSAGES.mustBeAfterRoundEndDate);
            }

            if (errorMessage) {
                return createError({
                    path,
                    message: errorMessage,
                });
            }
            return true;
        });
    },
);

yup.addMethod(
    yup.date,
    'validateLqasImEndDate',
    function validateLqasImEndDate(formatMessage) {
        return this.test('validateLqasImEndDate', '', (value, context) => {
            const keys = dateKeys.round;
            const { path, createError, parent } = context;
            const newEndDate = moment(value);
            const roundStartDate =
                parent[keys.start] && moment(parent[keys.start], dateFormat);

            let errorMessage;

            if (roundStartDate?.isAfter(newEndDate)) {
                errorMessage = formatMessage(MESSAGES.endDateBeforeStartDate);
            }

            if (errorMessage) {
                return createError({
                    path,
                    message: errorMessage,
                });
            }
            return true;
        });
    },
);

yup.addMethod(
    yup.date,
    'validateEndDate',
    // Add round to args and uncomment code to enable restriction based on round dates
    function validateEndDate(formatMessage, dateType = 'round') {
        return this.test('validateEndDate', '', (value, context) => {
            const keys = dateKeys[dateType];
            const { path, createError, parent } = context;
            const newEndDate = moment(value);
            const startDate =
                parent[keys.start] && moment(parent[keys.start], dateFormat);
            let errorMessage;

            if (startDate?.isAfter(newEndDate)) {
                errorMessage = formatMessage(MESSAGES.endDateBeforeStartDate);
            }

            if (errorMessage) {
                return createError({
                    path,
                    message: errorMessage,
                });
            }
            return true;
        });
    },
);

export const useSubActivityValidation = (): yup.ObjectSchema<any> => {
    const { formatMessage } = useSafeIntl();
    return useMemo(
        () =>
            yup.object().shape({
                name: yup
                    .string()
                    .nullable()
                    .required(formatMessage(MESSAGES.fieldRequired)),
                start_date: yup
                    .date()
                    .typeError(formatMessage(MESSAGES.invalidDate))
                    .nullable()
                    // start should be before end
                    // start should not be before round start
                    // @ts-ignore
                    .validateStartDate(formatMessage)
                    .required(formatMessage(MESSAGES.fieldRequired)),
                end_date: yup
                    .date()
                    .typeError(formatMessage(MESSAGES.invalidDate))
                    .nullable()
                    // end should be after start
                    // end should not be after round end
                    // @ts-ignore
                    .validateEndDate(formatMessage)
                    .required(formatMessage(MESSAGES.fieldRequired)),
                lqas_started_at: yup
                    .date()
                    .typeError(formatMessage(MESSAGES.invalidDate))
                    .nullable()
                    // start should be before end
                    // start should not be before round start
                    // @ts-ignore
                    .validateStartDate(formatMessage, 'lqas')
                    // lqas/im cannot start before the round/subactivity has ended
                    .validateLqasImStartDate(formatMessage),
                lqas_ended_at: yup
                    .date()
                    .typeError(formatMessage(MESSAGES.invalidDate))
                    .nullable()
                    // end should be after start
                    // end should not be after round end
                    // @ts-ignore
                    .validateLqasImEndDate(formatMessage)
                    .validateEndDate(formatMessage, 'lqas'),
                im_started_at: yup
                    .date()
                    .typeError(formatMessage(MESSAGES.invalidDate))
                    .nullable()
                    // start should be before end
                    // start should not be before round start
                    // @ts-ignore
                    .validateStartDate(formatMessage, 'im')
                    // lqas/im cannot start before the round/subactivity has ended
                    .validateLqasImStartDate(formatMessage),
                im_ended_at: yup
                    .date()
                    .typeError(formatMessage(MESSAGES.invalidDate))
                    .nullable()
                    // end should be after start
                    // end should not be after round end
                    // @ts-ignore
                    .validateLqasImEndDate(formatMessage)
                    .validateEndDate(formatMessage, 'im'),
                age_unit: yup.string().nullable(),
                age_min: yup.number().nullable(),
                age_max: yup.number().nullable(),
            }),
        [formatMessage],
    );
};
