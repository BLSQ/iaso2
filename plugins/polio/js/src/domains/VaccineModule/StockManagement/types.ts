import { UrlParams } from 'bluesquare-components';

export type StockManagementListParams = {
    order?: string;
    pageSize?: string; // number as string
    page?: string; // number as string
    accountId: string; // number as string
    search?: string;
    country_id?: string; // number as string
    vaccine_type?: string;
};

export type TabValue = 'usableVials' | 'unusableVials' | 'earmarked';

export type StockManagementDetailsParams = Partial<UrlParams> & {
    id: string; // number as string
    tab?: TabValue;
    unusableVialsPageSize?: string; // number as string
    unusableVialsPage?: string; // number as string
    unusableVialsOrder?: string;
    usableVialsPageSize?: string; // number as string
    usableVialsPage?: string; // number as string
    usableVialsOrder?: string;
    earmarkedPageSize?: string; // number as string
    earmarkedPage?: string; // number as string
    earmarkedOrder?: string;
};

export type StockVariationTab =
    | 'forma'
    | 'destruction'
    | 'incident'
    | 'earmarked';

export type StockVariationParams = {
    id: string; // number as string
    tab: StockVariationTab;
    formaPageSize: string; // number as string
    formaPage: string; // number as string
    formaOrder: string;
    destructionPageSize: string; // number as string
    destructionPage: string; // number as string
    destructionOrder: string;
    incidentPageSize: string; // number as string
    incidentPage: string; // number as string
    incidentOrder: string;
    unusableVialsOrder: string; // number as string
    usableVialsPageSize: string; // number as string
    usableVialsPage: string; // number as string
    usableVialsOrder: string; // number as string
    earmarkedPageSize?: string; // number as string
    earmarkedPage?: string; // number as string
    earmarkedOrder?: string;
};
