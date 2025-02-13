import React, { ReactElement } from 'react';
import { Box } from '@mui/material';
import { IntlFormatMessage, useSafeIntl } from 'bluesquare-components';
import { upperCase } from 'lodash';
import moment from 'moment';
import { Link } from 'react-router-dom';
import { GeoJsonMap } from '../../../../../../../hat/assets/js/apps/Iaso/components/maps/GeoJsonMapComponent';
import { LinkToOrgUnit } from '../../../../../../../hat/assets/js/apps/Iaso/domains/orgUnits/components/LinkToOrgUnit';
import { useGetOrgUnitDetail } from '../../../../../../../hat/assets/js/apps/Iaso/domains/orgUnits/hooks/requests/useGetOrgUnitDetail';
import MESSAGES from '../../../constants/messages';

type OrgUnitLinkProps = {
    orgUnitId: number;
};

const OrgUnitLink = ({ orgUnitId }): ReactElement<OrgUnitLinkProps> => {
    const { data: currentOrgUnit } = useGetOrgUnitDetail(orgUnitId);

    return <LinkToOrgUnit orgUnit={currentOrgUnit} />;
};

const convertBoolean = (value: boolean, formatMessage: IntlFormatMessage) => {
    return value ? formatMessage(MESSAGES.yes) : formatMessage(MESSAGES.no);
};

const convertDate = (value: string, format = 'L') => {
    return value ? moment(value).format(format) : '--';
};
export const useGetConfig = (): Record<string, any> => {
    const { formatMessage } = useSafeIntl();
    return [
        // Global
        {
            key: 'id',
        },
        {
            key: 'created_at',
            getLogValue: log => convertDate(log.created_at, 'LTS'),
        },
        {
            key: 'updated_at',
            getLogValue: log => convertDate(log.updated_at, 'LTS'),
        },
        {
            key: 'deleted_at',
            getLogValue: log => convertDate(log.deleted_at, 'LTS'),
        },
        {
            key: 'account',
        },
        // Base Info
        {
            key: 'epid',
        },
        {
            key: 'obr_name',
        },
        {
            key: 'group',
            type: 'object',
            childrenLabel: MESSAGES.group,
            children: [
                {
                    key: 'id',
                },
                {
                    key: 'org_units',
                    getLogValue: log =>
                        log.org_units.map((ouId, index) => {
                            const lastArrayItem =
                                log.org_units[log.org_units.length - 1];
                            return (
                                <Box key={ouId} display="inline-block">
                                    <Link
                                        target="_blank"
                                        href={`/dashboard/orgunits/detail/orgUnitId/${ouId}`}
                                    >
                                        {ouId}
                                    </Link>
                                    {log.org_units[index] !== lastArrayItem &&
                                        ','}
                                </Box>
                            );
                        }),
                },
            ],
        },
        {
            key: 'description',
        },
        {
            key: 'gpei_coordinator',
        },
        {
            key: 'gpei_email',
        },
        {
            key: 'country',
            getLogValue: log => <OrgUnitLink orgUnitId={log.country} />,
        },
        {
            key: 'initial_org_unit',
            getLogValue: log => (
                <OrgUnitLink orgUnitId={log.initial_org_unit} />
            ),
        },
        {
            key: 'onset_at',
            getLogValue: log => convertDate(log.onset_at),
        },
        {
            key: 'cvdpv2_notified_at',
            getLogValue: log => convertDate(log.cvdpv2_notified_at),
        },
        {
            key: 'virus',
        },
        {
            key: 'is_preventive',
            getLogValue: log =>
                convertBoolean(log.is_preventive, formatMessage),
        },
        {
            key: 'is_test',
            getLogValue: log => convertBoolean(log.is_test, formatMessage),
        },
        {
            key: 'enable_send_weekly_email',
            getLogValue: log =>
                convertBoolean(log.enable_send_weekly_email, formatMessage),
        },
        {
            key: 'pv_notified_at', // deprecated
            getLogValue: log => convertDate(log.pv_notified_at),
        },
        {
            key: 'outbreak_declaration_date',
            getLogValue: log => convertDate(log.outbreak_declaration_date),
        },
        // Detection
        {
            key: 'detection_status',
        },
        {
            key: 'detection_responsible',
        },
        {
            key: 'pv2_notified_at', // deprecated
            getLogValue: log => convertDate(log.pv2_notified_at),
        },

        // Risk assessment
        {
            key: 'risk_assessment_status',
        },
        {
            key: 'verification_score',
        },
        {
            key: 'investigation_at',
            getLogValue: log => convertDate(log.investigation_at),
        },
        {
            key: 'risk_assessment_first_draft_submitted_at',
            getLogValue: log =>
                convertDate(log.risk_assessment_first_draft_submitted_at),
        },
        {
            key: 'three_level_call_at', // deprecated
            getLogValue: log => convertDate(log.three_level_call_at),
        },
        {
            key: 'risk_assessment_rrt_oprtt_approval_at',
            getLogValue: log =>
                convertDate(log.risk_assessment_rrt_oprtt_approval_at),
        },
        {
            key: 'ag_nopv_group_met_at',
            getLogValue: log => convertDate(log.ag_nopv_group_met_at),
        },
        {
            key: 'dg_authorized_at',
            getLogValue: log => convertDate(log.dg_authorized_at),
        },
        {
            key: 'risk_assessment_responsible',
        },
        {
            key: 'doses_request', // deprecated
        },
        // Budget
        {
            key: 'budget_status_at_WFEDITABLE',
            getLogValue: log => upperCase(log.budget_status),
        },
        {
            key: 'budget_current_state_label_at_WFEDITABLE',
        },
        // Budget request
        {
            key: 'who_sent_budget_at_WFEDITABLE',
            getLogValue: log => convertDate(log.who_sent_budget_at_WFEDITABLE),
        },
        {
            key: 'unicef_sent_budget_at_WFEDITABLE',
            getLogValue: log =>
                convertDate(log.unicef_sent_budget_at_WFEDITABLE, 'L'),
        },
        {
            key: 'gpei_consolidated_budgets_at_WFEDITABLE',
            getLogValue: log =>
                convertDate(log.gpei_consolidated_budgets_at_WFEDITABLE, 'L'),
        },
        // RRT review
        {
            key: 'submitted_to_rrt_at_WFEDITABLE',
            getLogValue: log =>
                convertDate(log.submitted_to_rrt_at_WFEDITABLE, 'L'),
        },
        {
            key: 'feedback_sent_to_gpei_at_WFEDITABLE',
            getLogValue: log =>
                convertDate(log.feedback_sent_to_gpei_at_WFEDITABLE, 'L'),
        },
        {
            key: 're_submitted_to_rrt_at_WFEDITABLE',
            getLogValue: log =>
                convertDate(log.re_submitted_to_rrt_at_WFEDITABLE, 'L'),
        },
        // ORPG review
        {
            key: 'submitted_to_orpg_operations1_at_WFEDITABLE',
            getLogValue: log =>
                convertDate(
                    log.submitted_to_orpg_operations1_at_WFEDITABLE,
                    'L',
                ),
        },
        {
            key: 'feedback_sent_to_rrt1_at_WFEDITABLE',
            getLogValue: log =>
                convertDate(log.feedback_sent_to_rrt1_at_WFEDITABLE, 'L'),
        },
        {
            key: 're_submitted_to_orpg_operations1_at_WFEDITABLE',
            getLogValue: log =>
                convertDate(
                    log.re_submitted_to_orpg_operations1_at_WFEDITABLE,
                    'L',
                ),
        },
        {
            key: 'submitted_to_orpg_wider_at_WFEDITABLE',
            getLogValue: log =>
                convertDate(log.submitted_to_orpg_wider_at_WFEDITABLE, 'L'),
        },
        {
            key: 'submitted_to_orpg_operations2_at_WFEDITABLE',
            getLogValue: log =>
                convertDate(
                    log.submitted_to_orpg_operations2_at_WFEDITABLE,
                    'L',
                ),
        },
        {
            key: 'feedback_sent_to_rrt2_at_WFEDITABLE',
            getLogValue: log =>
                convertDate(log.feedback_sent_to_rrt2_at_WFEDITABLE, 'L'),
        },
        {
            key: 're_submitted_to_orpg_operations2_at_WFEDITABLE',
            getLogValue: log =>
                convertDate(
                    log.re_submitted_to_orpg_operations2_at_WFEDITABLE,
                    'L',
                ),
        },
        // APPROVAL
        {
            key: 'submitted_for_approval_at_WFEDITABLE',
            getLogValue: log =>
                convertDate(log.submitted_for_approval_at_WFEDITABLE, 'L'),
        },
        {
            key: 'feedback_sent_to_orpg_operations_unicef_at_WFEDITABLE',
            getLogValue: log =>
                convertDate(
                    log.feedback_sent_to_orpg_operations_unicef_at_WFEDITABLE,
                    'L',
                ),
        },
        {
            key: 'feedback_sent_to_orpg_operations_who_at_WFEDITABLE',
            getLogValue: log =>
                convertDate(
                    log.feedback_sent_to_orpg_operations_who_at_WFEDITABLE,
                    'L',
                ),
        },
        {
            key: 'approved_by_who_at_WFEDITABLE',
            getLogValue: log => convertDate(log.approved_by_who_at_WFEDITABLE),
        },
        {
            key: 'approved_by_unicef_at_WFEDITABLE',
            getLogValue: log =>
                convertDate(log.approved_by_unicef_at_WFEDITABLE),
        },
        {
            key: 'approved_at_WFEDITABLE',
            getLogValue: log => convertDate(log.approved_at_WFEDITABLE),
        },
        {
            key: 'approval_confirmed_at_WFEDITABLE',
            getLogValue: log =>
                convertDate(log.approval_confirmed_at_WFEDITABLE),
        },
        {
            key: 'payment_mode',
        },
        {
            key: 'who_disbursed_to_co_at',
            getLogValue: log => convertDate(log.who_disbursed_to_co_at),
        },
        {
            key: 'unicef_disbursed_to_co_at',
            getLogValue: log => convertDate(log.unicef_disbursed_to_co_at),
        },
        {
            key: 'unicef_disbursed_to_moh_at',
            getLogValue: log => convertDate(log.unicef_disbursed_to_moh_at),
        },
        {
            key: 'who_disbursed_to_moh_at',
            getLogValue: log => convertDate(log.who_disbursed_to_moh_at),
        },
        {
            key: 'district_count',
        },
        {
            key: 'no_regret_fund_amount',
        },
        // Scopes
        {
            key: 'scopes',
            type: 'array',
            childrenLabel: MESSAGES.scope,
            children: [
                {
                    key: 'id',
                },
                {
                    key: 'group',
                    type: 'object',
                    childrenLabel: MESSAGES.group,
                    children: [
                        {
                            key: 'id',
                        },
                        {
                            key: 'org_units',
                            getLogValue: log =>
                                log.org_units.map((ouId, index) => {
                                    const lastArrayItem =
                                        log.org_units[log.org_units.length - 1];
                                    return (
                                        <Box key={ouId} display="inline-block">
                                            <Link
                                                target="_blank"
                                                href={`/dashboard/orgunits/detail/orgUnitId/${ouId}`}
                                            >
                                                {ouId}
                                            </Link>
                                            {log.org_units[index] !==
                                                lastArrayItem && ','}
                                        </Box>
                                    );
                                }),
                        },
                    ],
                },
            ],
        },
        {
            key: 'separate_scopes_per_round',
            getLogValue: log =>
                convertBoolean(log.separate_scopes_per_round, formatMessage),
        },
        // Rounds
        {
            key: 'rounds',
            type: 'array',
            childrenLabel: MESSAGES.round,
            children: [
                {
                    key: 'id',
                },
                {
                    key: 'cost',
                },
                {
                    key: 'number',
                },
                {
                    key: 'started_at',
                    getLogValue: log => convertDate(log.started_at),
                },
                {
                    key: 'ended_at',
                    getLogValue: log => convertDate(log.ended_at),
                },
                {
                    key: 'mop_up_started_at',
                    getLogValue: log => convertDate(log.mop_up_started_at),
                },
                {
                    key: 'mop_up_ended_at',
                    getLogValue: log => convertDate(log.mop_up_ended_at),
                },
                {
                    key: 'im_started_at',
                    getLogValue: log => convertDate(log.im_started_at),
                },
                {
                    key: 'im_ended_at',
                    getLogValue: log => convertDate(log.im_ended_at),
                },
                {
                    key: 'lqas_started_at',
                    getLogValue: log => convertDate(log.lqas_started_at),
                },
                {
                    key: 'lqas_ended_at',
                    getLogValue: log => convertDate(log.lqas_ended_at),
                },
                {
                    key: 'percentage_covered_target_population',
                },
                {
                    key: 'lqas_district_passing',
                },
                {
                    key: 'lqas_district_failing',
                },
                {
                    key: 'main_awareness_problem',
                },
                {
                    key: 'im_percentage_children_missed_in_household',
                },
                {
                    key: 'im_percentage_children_missed_out_household',
                },
                {
                    key: 'awareness_of_campaign_planning',
                },
                {
                    key: 'scopes',
                    type: 'array',
                    childrenLabel: MESSAGES.scope,
                    children: [
                        {
                            key: 'id',
                        },
                        {
                            key: 'group',
                            type: 'object',
                            childrenLabel: MESSAGES.group,
                            children: [
                                {
                                    key: 'id',
                                },
                                {
                                    key: 'org_units',
                                    getLogValue: log =>
                                        log.org_units.map((ouId, index) => {
                                            const lastArrayItem =
                                                log.org_units[
                                                    log.org_units.length - 1
                                                ];
                                            return (
                                                <Link
                                                    target="_blank"
                                                    href={`/dashboard/orgunits/detail/orgUnitId/${ouId}`}
                                                >
                                                    {ouId}
                                                    {log.org_units[index] !==
                                                        lastArrayItem && ','}
                                                </Link>
                                            );
                                        }),
                                },
                            ],
                        },
                    ],
                },
                {
                    key: 'campaign',
                },
                // Vaccines
                {
                    key: 'vaccines',
                    type: 'array',
                    childrenLabel: MESSAGES.vaccine,
                    children: [
                        {
                            key: 'id',
                        },
                        {
                            key: 'dosesPerVial',
                        },
                        {
                            key: 'name',
                        },
                        {
                            key: 'round',
                        },
                        {
                            key: 'wastageRatio',
                        },
                    ],
                },
                {
                    key: 'reporting_delays_hc_to_district',
                },
                {
                    key: 'reporting_delays_district_to_region',
                },
                {
                    key: 'reporting_delays_region_to_national',
                },
                {
                    key: 'shipments',
                    type: 'array',
                    childrenLabel: MESSAGES.shipment,
                    children: [
                        {
                            key: 'id',
                        },
                        {
                            key: 'round',
                        },
                        {
                            key: 'po_numbers',
                        },
                        {
                            key: 'vaccine_name',
                        },
                        {
                            key: 'receptionVaccineArrivalReport',
                            getLogValue: log => convertDate(log.date_reception),
                        },
                        {
                            key: 'vials_received',
                        },
                        {
                            key: 'receptionPreAlert',
                            getLogValue: log =>
                                convertDate(log.reception_pre_alert),
                        },
                        {
                            key: 'estimatedDateOfArrival',
                            getLogValue: log =>
                                convertDate(log.estimated_arrival_date),
                        },
                        {
                            key: 'comment',
                        },
                    ],
                },
                {
                    key: 'forma_reception',
                    getLogValue: log => convertDate(log.forma_reception),
                },
                {
                    key: 'forma_date',
                    getLogValue: log => convertDate(log.forma_date),
                },
                {
                    key: 'forma_unusable_vials',
                },
                {
                    key: 'forma_usable_vials',
                },
                {
                    key: 'forma_missing_vials',
                },
                {
                    key: 'forma_comment',
                },
                // Destructions
                {
                    key: 'destructions',
                    type: 'array',
                    childrenLabel: MESSAGES.destruction,
                    children: [
                        {
                            key: 'id',
                        },
                        {
                            key: 'round',
                        },
                        {
                            key: 'destructionReceptionDate',
                            getLogValue: log =>
                                convertDate(log.date_report_received),
                        },
                        {
                            key: 'destructionReportDate',
                            getLogValue: log => convertDate(log.date_report),
                        },
                        {
                            key: 'vials_destroyed',
                        },
                        {
                            key: 'comment',
                        },
                    ],
                },
                {
                    key: 'preparedness_spreadsheet_url',
                },
            ],
        },
        {
            key: 'geojson',
            getLogValue: log => {
                const hasGeoJson =
                    log.geojson !== undefined && log.geojson.length > 0;

                if (hasGeoJson) {
                    return <GeoJsonMap geoJson={log.geojson} />;
                }
                return formatMessage(MESSAGES.noGeojson);
            },
        },
        {
            key: 'creation_email_send_at',
            getLogValue: log => convertDate(log.creation_email_send_at),
        },
    ];
};
