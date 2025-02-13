import { useMemo } from 'react';
import { Theme } from '@mui/material';
import { last } from 'lodash';
import pluginsConfigs from '../../../../../../../plugins';
import { Plugin } from '../types';

export const usePlugins = (
    pluginsKeys: string[],
): {
    plugins: Plugin[];
    pluginHomePage: string | undefined;
    pluginTheme: Theme | undefined;
} => {
    return useMemo(() => {
        const plugins: Plugin[] = pluginsKeys
            .map(pluginsKey => {
                const pluginConfig: Plugin = pluginsConfigs[pluginsKey];
                return pluginConfig
                    ? { ...pluginConfig, key: pluginsKey }
                    : null;
            })
            .filter(Boolean) as Plugin[];

        const pluginHomePage = last(plugins.map(plugin => plugin.homeUrl));
        const pluginTheme = last(plugins.map(plugin => plugin.theme));

        return { plugins, pluginHomePage, pluginTheme };
    }, [pluginsKeys]);
};
