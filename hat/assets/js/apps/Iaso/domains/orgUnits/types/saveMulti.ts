import { OrgunitType } from './orgunitTypes';
import { Search } from './search';

export type SaveData = {
    groups_added?: Array<number>;
    groups_removed?: Array<number>;
    org_unit_type?: OrgunitType;
    validation_status?: string;
    selected_ids?: Array<number>;
    unselected_ids?: Array<number>;
    select_all?: boolean;
    searches?: [Search];
};
