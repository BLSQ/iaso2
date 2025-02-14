import { Pagination } from 'bluesquare-components';
import { User } from '../../../utils/usersUtils';
import { Beneficiary } from '../../entities/types/beneficiary';
import { OrgUnitChangeRequest } from '../../orgUnits/reviewChanges/types';
import { OrgUnit } from '../../orgUnits/types/orgUnit';

type Lock = {
    id: number;
    locked_by: User;
    unlocked_by?: User;
    top_org_unit: {
        name: string;
    };
};
export type ShortFile = {
    itemId: number;
    createdAt: number;
    path: string;
    file_type?: MimeType;
};

export type File = {
    id: number;
    instance_id: number;
    file: string;
    created_at: number;
    file_type: MimeType;
};

export type Instance = {
    uuid: string;
    id: number;
    device_id: string;
    file_name: string;
    file_url: string;
    form_id: number;
    form_name: string;
    created_at: number;
    updated_at: number;
    latitude: number;
    longitude: number;
    altitude: number;
    accuracy: number;
    files: string[];
    status: string;
    export_statuses: Array<string>;
    correlation_id?: string;
    deleted: boolean;
    org_unit: OrgUnit;
    period?: string;
    file_content: Record<string, any>;
    form_descriptor: Record<string, unknown>;
    last_export_success_at: unknown;
    instance_locks: Lock[];
    can_user_modify: boolean;
    is_locked: boolean;
    is_instance_of_reference_form: boolean;
    is_reference_instance: boolean;
    entity: Beneficiary;
    source_created_at: number;
    change_requests: Array<OrgUnitChangeRequest>;
};

export type InstanceLogDetail = {
    id: number;
    content_type: string;
    object_id: string;
    source: string;
    user?: User;
    created_at: string;
};

export type InstanceLogsDetail = Pagination & {
    list: Array<InstanceLogDetail>;
};

type NewValue = {
    fields: Record<string, any>;
};

export type InstanceLogData = {
    id: number;
    content_type: string;
    object_id: string;
    new_value: NewValue[];
    source: string;
    user: User;
    possible_fields: Record<string, any>[];
    files: string[];
};

type FormVersions = {
    descriptor: Record<string, any>;
};
export type FormDescriptor = {
    form_versions: FormVersions[];
};

export type FileContent = {
    logA: Record<string, any>;
    logB: Record<string, any>;
    logAFiles: string[];
    logBFiles: string[];
    fields: Record<string, any>[];
};
export interface PaginatedInstances extends Pagination {
    instances: Instance[];
}

export type CheckBulkGpsPushResult = {
    result: string;
    warning_no_location?: number[];
    warning_overwrite?: number[];
    error_ids?: number[];
};
export type MimeType =
    // Text
    | 'text/plain'
    | 'text/html'
    | 'text/css'
    | 'text/javascript'
    // Image
    | 'image/jpeg'
    | 'image/png'
    | 'image/gif'
    | 'image/svg+xml'
    | 'image/webp'
    // Audio
    | 'audio/mpeg'
    | 'audio/ogg'
    | 'audio/wav'
    // Video
    | 'video/mp4'
    | 'video/mpeg'
    | 'video/webm'
    | 'video/ogg'
    // Application
    | 'application/json'
    | 'application/xml'
    | 'application/zip'
    | 'application/pdf'
    | 'application/sql'
    | 'application/graphql'
    | 'application/ld+json'
    | 'application/msword'
    | 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    | 'application/vnd.ms-excel'
    | 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    | 'application/vnd.ms-powerpoint'
    | 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    // Font
    | 'font/ttf'
    | 'font/woff'
    | 'font/woff2'
    // Other
    | 'application/octet-stream'
    | 'multipart/form-data'
    | 'application/x-www-form-urlencoded';
