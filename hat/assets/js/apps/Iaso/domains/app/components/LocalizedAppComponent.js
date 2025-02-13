/* eslint-disable import/no-relative-packages */
import React, { useContext } from 'react';
import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import PropTypes from 'prop-types';
import { IntlProvider } from 'react-intl';

// the intl paths get rewritten by webpack depending on the locale
import en from '__intl/messages/en'; // eslint-disable-line
import fr from '__intl/messages/fr'; // eslint-disable-line

import enLibrary from '../../../../../../../../node_modules/bluesquare-components/dist/locale/en.json';
import frLibrary from '../../../../../../../../node_modules/bluesquare-components/dist/locale/fr.json';
import { PluginsContext } from '../../../plugins/context';
import { useLocale } from '../contexts/LocaleContext.tsx';

const extractTranslations = (plugins, key) => {
    return plugins
        .map(plugin => plugin.translations[key])
        .reduce((v1, v2) => ({ ...v1, ...v2 }), {});
};
export default function LocalizedAppComponent({ children }) {
    const { plugins } = useContext(PluginsContext);
    const frPlugins = extractTranslations(plugins, 'fr');
    const enPlugins = extractTranslations(plugins, 'en');
    const messages = {
        fr: { ...fr, ...frLibrary, ...frPlugins },
        en: { ...en, ...enLibrary, ...enPlugins },
    };
    const { locale } = useLocale();
    const onError = msg => console.warn(msg);
    return (
        <IntlProvider
            onError={onError}
            key={locale}
            locale={locale}
            messages={messages[locale]}
        >
            <LocalizationProvider
                dateAdapter={AdapterMoment}
                adapterLocale={locale}
            >
                {children}
            </LocalizationProvider>
        </IntlProvider>
    );
}
LocalizedAppComponent.propTypes = {
    children: PropTypes.any.isRequired,
};
