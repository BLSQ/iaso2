/* eslint-disable camelcase */
import { Vaccine } from '../../../constants/types';
import { Optional } from '../../../../../../../hat/assets/js/apps/Iaso/types/utils';

export type TabValue = 'vrf' | 'arrival_reports' | 'pre_alerts';

export type VRF = {
    id?: number;
    country: number;
    campaign: string;
    vaccine_type: Vaccine;
    rounds: string; // 1,2
    date_vrf_signature: string; // date in string form
    quantities_ordered_in_doses: number;
    wastage_rate_used_on_vrf: number;
    date_vrf_reception: string; // date in string form
    date_vrf_submission_orpg?: string; // date in string form
    quantities_approved_by_orpg_in_doses?: number;
    date_rrt_orpg_approval?: string; // date in string form
    date_vrf_submission_dg?: string; // date in string form
    quantities_approved_by_dg_in_doses?: number;
    date_dg_approval?: string; // date in string form
    comments?: string;
};

export type PreAlert = {
    id?: number;
    date_reception: string; // date in string form
    po_number: string;
    eta: string;
    lot_number: number;
    expiration_date: string; // date in string form
    doses_shipped: number;
    doses_recieved: number;
    doses_per_vial: number;
    to_delete?: boolean;
};

export type VAR = {
    id?: number;
    report_date: string; // date in string form
    po_number: number;
    lot_number: number;
    expiration_date: string; // date in string form
    doses_shipped: number;
    doses_received: number;
    doses_per_vial: number;
    to_delete?: boolean;
};

export type SupplyChainFormData = {
    vrf: Optional<Partial<VRF>>;
    pre_alerts: Optional<Partial<PreAlert>[]>;
    arrival_reports: Optional<Partial<VAR>[]>;
    activeTab: TabValue;
    saveAll: boolean;
    changedTabs: TabValue[];
};
