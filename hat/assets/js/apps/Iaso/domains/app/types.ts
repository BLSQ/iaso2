import { ElementType, ReactNode } from 'react';
import { Theme } from '@mui/material/styles';
import { IntlMessage } from 'bluesquare-components';
import {
    RouteCustom,
    Redirection as RoutingRedirection,
} from '../../routing/types';

export type MenuItem = {
    label: string | IntlMessage;
    permissions?: string[];
    key?: string;
    mapKey?: string;
    icon?: (props: Record<string, any>) => ReactNode;
    subMenu?: MenuItems;
    extraPath?: string;
    url?: string;
    isActive?: (pathname: string) => boolean;
    dev?: boolean;
};
export type MenuItems = MenuItem[];

// TODO deprecate or update to react-router 6
export type Redirection = {
    path: string;
    component: (args: any) => ReactNode;
};

export type Plugin = {
    routes: RouteCustom[];
    menu: MenuItem[];
    translations: Record<string, any>;
    homeUrl?: string;
    homeOnline?: ElementType;
    homeOffline?: ElementType;
    key?: string;
    baseUrls: Record<string, string>;
    paramsConfig: Record<string, string[]>;
    redirections?: RoutingRedirection[];
    theme?: Theme;
    customComponents?: {
        key: string;
        component: ElementType;
    }[];
};

export type Plugins = {
    plugins: Plugin[];
};

export type PaginatedResponse<T> = {
    hasPrevious?: boolean;
    hasNext?: boolean;
    count?: number;
    page?: number;
    pages?: number;
    limit?: number;
    results?: T[];
};
