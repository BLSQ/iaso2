import { createContext } from 'react';
import { textPlaceholder } from 'bluesquare-components';
import pluginsConfigs from '../../../../../../plugins';
import { Plugin } from '../domains/app/types';
import {
    Beneficiary,
    FileContent,
} from '../domains/entities/types/beneficiary';
import { FormDescriptor } from '../domains/forms/types/forms';
import { formatLabel } from '../domains/instances/utils';

export const getYears = (
    yearsCount: number,
    offset = 0,
    reverse = false,
): number[] => {
    const currentYear = new Date().getFullYear() + offset;
    const years = Array(yearsCount)
        .fill(null)
        .map((y, i) => currentYear - i);
    if (reverse) {
        return years.reverse();
    }
    return years;
};

export const userHasPermission = (
    permissions: any[],
    currentUser: any,
    permissionKey: string,
    allowSuperUser = true,
): boolean => {
    let hasPermission = false;
    if (
        currentUser &&
        permissions &&
        Object.getOwnPropertyNames(currentUser).length !== 0 &&
        permissions.length > 0
    ) {
        const currentPermission = permissions.find(
            p => p.codename === permissionKey,
        );
        // TODO: the API is now filtering the user permissions list so the second .find below is unnecessary
        if (
            (currentUser.is_superuser && allowSuperUser) ||
            (currentPermission &&
                currentUser.permissions.find(p => p === currentPermission.id))
        ) {
            hasPermission = true;
        }
    }
    return hasPermission;
};

export const getPlugins = (pluginsKeys: string[]): any[] => {
    const plugins: Plugin[] = [];
    pluginsKeys.forEach(pluginsKey => {
        const pluginConfig: Plugin = pluginsConfigs[pluginsKey];
        if (pluginConfig) {
            plugins.push({
                ...pluginConfig,
                key: pluginsKey,
            });
        }
    });
    return plugins;
};

export const PluginsContext = createContext<{ plugins: Plugin[] }>({
    plugins: [],
});

// create timeout to simulate async call
// credit https://stackoverflow.com/questions/51200626/using-a-settimeout-in-a-async-function
// Added it here because using the one from test/utils would cause compilation errors
export const waitFor = (delay: number): Promise<void> =>
    new Promise(resolve => setTimeout(resolve, delay));

export const fakeResponse =
    (response: any) =>
    async (isError = false): Promise<any> => {
        if (isError) throw new Error('mock request failed');
        await waitFor(200);
        return response;
    };

export const noOp = (): void => undefined;

export const findDescriptorInChildren = (field: any, descriptor: any): any => {
    const fieldName = typeof field === 'string' ? field : field.name;
    return descriptor?.children?.reduce((a, child) => {
        if (a) return a;
        if (child.name === fieldName) return child;
        if (child.children) return findDescriptorInChildren(field, child);
        return undefined;
    }, null);
};

export const getDescriptorValue = (
    fieldKey: string,
    fileContent: FileContent | Beneficiary,
    formDescriptors?: FormDescriptor[],
): string => {
    let value = textPlaceholder;
    if (fileContent[fieldKey]) {
        formDescriptors?.forEach(formDescriptor => {
            const descriptor = findDescriptorInChildren(
                fieldKey,
                formDescriptor,
            );
            if (descriptor?.children) {
                const descriptorValue = descriptor.children.find(
                    child => fileContent[fieldKey] === child.name,
                );
                if (descriptorValue) {
                    value = formatLabel(descriptorValue);
                }
            }
        });
    }
    return value;
};
