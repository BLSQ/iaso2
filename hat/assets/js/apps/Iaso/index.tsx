import React from 'react';
import { GlobalStyles } from '@mui/material';
import CssBaseline from '@mui/material/CssBaseline';
import { ThemeProvider } from '@mui/material/styles';
import { theme } from 'bluesquare-components';
import { SnackbarProvider } from 'notistack';
import ReactDOM from 'react-dom';
import { QueryClient, QueryClientProvider } from 'react-query';

import './libs/polyfills';

import LocalizedAppComponent from './domains/app/components/LocalizedAppComponent';
import { LocaleProvider } from './domains/app/contexts/LocaleContext';
import { SentryConfig } from './domains/app/contexts/SentryProvider';
import { SidebarProvider } from './domains/app/contexts/SideBarContext';
import {
    ThemeConfig,
    ThemeConfigContext,
} from './domains/app/contexts/ThemeConfigContext';
import App from './domains/app/index';
import { PluginsContext } from './plugins/context';
import { usePlugins } from './plugins/hooks/usePlugins';
import { getGlobalOverrides, getOverriddenTheme } from './styles';

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
        },
    },
});

declare global {
    interface Window {
        SENTRY_CONFIG?: SentryConfig;
        SENTRY_INITIALIZED?: boolean;
        iasoApp: (
            element: HTMLElement,
            enabledPluginsName: string[],
            themeConfig: ThemeConfig,
            userHomePage: string,
        ) => void;
    }
}

const IasoApp: React.FC<{
    element: HTMLElement;
    enabledPluginsName: string[];
    themeConfig: ThemeConfig;
    userHomePage: string;
}> = ({ element, enabledPluginsName, themeConfig, userHomePage }) => {
    const { plugins, pluginHomePage, pluginTheme } =
        usePlugins(enabledPluginsName);
    const usedTheme = pluginTheme || getOverriddenTheme(theme, themeConfig);
    return ReactDOM.createPortal(
        <QueryClientProvider client={queryClient}>
            <PluginsContext.Provider value={{ plugins }}>
                <ThemeConfigContext.Provider value={themeConfig}>
                    <ThemeProvider theme={usedTheme}>
                        <CssBaseline />
                        <GlobalStyles styles={getGlobalOverrides(theme)} />
                        <SidebarProvider>
                            <LocaleProvider>
                                <LocalizedAppComponent>
                                    <SnackbarProvider
                                        maxSnack={3}
                                        autoHideDuration={4000}
                                        anchorOrigin={{
                                            vertical: 'bottom',
                                            horizontal: 'center',
                                        }}
                                    >
                                        <App
                                            userHomePage={
                                                pluginHomePage || userHomePage
                                            }
                                        />
                                    </SnackbarProvider>
                                </LocalizedAppComponent>
                            </LocaleProvider>
                        </SidebarProvider>
                    </ThemeProvider>
                </ThemeConfigContext.Provider>
            </PluginsContext.Provider>
        </QueryClientProvider>,
        element,
    );
};

window.iasoApp = (element, enabledPluginsName, themeConfig, userHomePage) => {
    ReactDOM.render(
        <IasoApp
            element={element}
            enabledPluginsName={enabledPluginsName}
            themeConfig={themeConfig}
            userHomePage={userHomePage}
        />,
        element,
    );
};
