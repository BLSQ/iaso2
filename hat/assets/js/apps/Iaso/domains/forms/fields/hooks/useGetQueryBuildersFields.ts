import { QueryBuilderFields } from 'bluesquare-components';

import { formatLabel } from '../../../instances/utils';

import { FormDescriptor, PossibleField } from '../../types/forms';

import { iasoFields, Field } from '../constants';
import { findDescriptorInChildren } from '../../../../utils';

export const useGetQueryBuildersFields = (
    formDescriptors?: FormDescriptor[],
    possibleFields?: PossibleField[],
    configFields: Field[] = iasoFields,
): QueryBuilderFields => {
    if (!possibleFields || !formDescriptors) return {};
    // you can fields examples here: https://codesandbox.io/s/github/ukrbublik/react-awesome-query-builder/tree/master/sandbox?file=/src/demo/config.tsx:1444-1464
    const fields: QueryBuilderFields = {};
    possibleFields.forEach(field => {
        const currentField: Field | undefined = configFields.find(
            iasoField =>
                iasoField.type === field.type || iasoField.alias === field.type,
        );
        if (
            currentField &&
            !currentField.disabled &&
            currentField.queryBuilder
        ) {
            fields[field.fieldKey] = {
                ...currentField.queryBuilder,
                label: `${formatLabel(field)} [${field.name}]`,
            };
            // in case the field needs a list of values to display
            if (currentField.useListValues) {
                // We will take the last found value in the form descriptors list
                formDescriptors?.forEach(formDescriptor => {
                    const descriptor = findDescriptorInChildren(
                        field,
                        formDescriptor,
                    );
                    if (descriptor?.children) {
                        const listValues =
                            descriptor.children.map(child => ({
                                value: child.name,
                                title: formatLabel(child),
                            })) || [];
                        // @ts-ignore
                        fields[field.fieldKey].fieldSettings = {
                            listValues,
                        };
                    }
                });
            }
        }
    });
    return fields;
};
