import { createContext } from 'react';
import { Plugin } from './types';

export const PluginsContext = createContext<{ plugins: Plugin[] }>({
    plugins: [],
});
