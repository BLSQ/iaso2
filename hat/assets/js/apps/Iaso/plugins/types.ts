import { ElementType } from 'react';
import { Theme } from '@mui/material/styles';
import { MenuItem } from '../domains/app/types';
import {
    RouteCustom,
    Redirection as RoutingRedirection,
} from '../routing/types';

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
