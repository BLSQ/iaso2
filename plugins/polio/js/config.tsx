import { Plugin } from '../../../hat/assets/js/apps/Iaso/domains/app/types';
import { Disclaimer } from './src/components/Disclaimer';
import { menu } from './src/constants/menu';
import { redirections } from './src/constants/redirections';
import { routes } from './src/constants/routes';
import en from './src/constants/translations/en.json';
import fr from './src/constants/translations/fr.json';
import {
    DASHBOARD_BASE_URL,
    baseUrls,
    paramsConfig,
} from './src/constants/urls';

const translations = {
    fr,
    en,
};

const config: Plugin = {
    baseUrls,
    paramsConfig,
    routes,
    redirections,
    menu,
    translations,
    homeUrl: `/${DASHBOARD_BASE_URL}/campaignCategory/all`,
    customComponents: [
        {
            key: 'topbar.disclaimer',
            component: Disclaimer,
        },
    ],
    // homeOffline: () => <div>OFFLINE</div>,
    // homeOnline: () => <div>CONNECTED HOME POLIO</div>,
};

export default config;
