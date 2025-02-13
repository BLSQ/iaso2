import React, {
    FunctionComponent,
    ReactElement,
    useCallback,
    useEffect,
    useMemo,
    useState,
} from 'react';
import { Box } from '@mui/material';
import { textPlaceholder, useSafeIntl } from 'bluesquare-components';
import orderBy from 'lodash/orderBy';
import moment from 'moment';
import { MarkerMap } from '../../../../components/maps/MarkerMapComponent';
import { BooleanValue, PlaceholderValue } from '../../../../libs/utils';
import { Nullable, Optional } from '../../../../types/utils';
import InstanceDetail from '../../../instances/compare/components/InstanceDetail';
import { LinkToOrgUnit } from '../../components/LinkToOrgUnit';
import { ShortOrgUnit } from '../../types/orgUnit';
import MESSAGES from '../messages';
import {
    InstanceForChangeRequest,
    NestedGroup,
    NestedLocation,
    NestedOrgUnitType,
    OrgUnitChangeRequestDetails,
} from '../types';

export type NewOrgUnitField = {
    key: string;
    isChanged: boolean;
    isSelected: boolean;
    newValue: ReactElement | Optional<Nullable<string>>;
    oldValue: ReactElement | Optional<Nullable<string>>;
    label: string;
    order: number;
    fieldType: string;
};
type FieldDefinition = {
    label: string;
    order: number;
    fieldType: string;
    formatValue: (
        val: any,
        isOld: boolean,
    ) => ReactElement | Optional<Nullable<string>>;
};

type FieldDefinitions = Record<string, FieldDefinition>;

type UseNewFields = {
    newFields: NewOrgUnitField[];
    setSelected: (key: string) => void;
};

type ReferenceInstancesProps = {
    instances: InstanceForChangeRequest[];
};

const ReferenceInstances: FunctionComponent<ReferenceInstancesProps> = ({
    instances,
}) => {
    return (
        <>
            {!instances || (instances.length === 0 && textPlaceholder)}
            {instances.map(instance => (
                <Box mb={1} key={instance.id}>
                    <InstanceDetail
                        instanceId={`${instance.id}`}
                        height="150px"
                        titleVariant="subtitle2"
                        titleColor="inherit"
                    />
                </Box>
            ))}
        </>
    );
};
const getGroupsValue = (groups: NestedGroup[]): ReactElement => {
    return (
        <>
            {groups && groups.length > 0
                ? groups.map(group => group.name).join(', ')
                : textPlaceholder}
        </>
    );
};

const getLocationValue = (
    location: NestedLocation,
    changeRequest: OrgUnitChangeRequestDetails,
    isOld: boolean,
): ReactElement => {
    const parent =
        !isOld && Boolean(changeRequest?.new_parent)
            ? changeRequest?.new_parent
            : changeRequest?.old_parent;
    return (
        <MarkerMap
            longitude={location.longitude}
            latitude={location.latitude}
            maxZoom={8}
            mapHeight={300}
            parent={parent}
        />
    );
};

const getPlaceholderValue = (key: string) => {
    if (key === 'location') {
        return <></>;
    }
    return PlaceholderValue;
};

const computeNewValue = (
    key: string,
    changeRequest: OrgUnitChangeRequestDetails,
    fieldDef: FieldDefinition,
    isChanged: boolean,
): Optional<Nullable<string>> | ReactElement => {
    if (!isChanged) {
        return changeRequest[`old_${key}`]
            ? fieldDef.formatValue(changeRequest[`old_${key}`], false)
            : getPlaceholderValue(key);
    }
    // This will not work if we have to show fields with boolean values
    return changeRequest[`new_${key}`]
        ? fieldDef.formatValue(changeRequest[`new_${key}`], false)
        : getPlaceholderValue(key);
};

export const useNewFields = (
    changeRequest?: OrgUnitChangeRequestDetails,
): UseNewFields => {
    const { formatMessage } = useSafeIntl();
    const [fields, setFields] = useState<NewOrgUnitField[]>([]);
    const fieldDefinitions: FieldDefinitions = useMemo(
        () => ({
            new_name: {
                label: formatMessage(MESSAGES.name),
                order: 1,
                fieldType: '',
                // span is necessary to enable text styling
                formatValue: val => <span>{val.toString()}</span>,
            },
            new_org_unit_type: {
                label: formatMessage(MESSAGES.orgUnitsType),
                order: 2,
                fieldType: 'string',
                // span is necessary to enable text styling
                formatValue: val => (
                    <span>{(val as NestedOrgUnitType)?.short_name}</span>
                ),
            },
            new_parent: {
                label: formatMessage(MESSAGES.parent),
                order: 3,
                fieldType: '',
                formatValue: val => (
                    <LinkToOrgUnit orgUnit={val as ShortOrgUnit} />
                ),
            },
            new_groups: {
                label: formatMessage(MESSAGES.groups),
                order: 4,
                fieldType: 'array',
                formatValue: val => (
                    <span>{getGroupsValue(val as NestedGroup[])}</span>
                ),
            },
            new_location: {
                label: formatMessage(MESSAGES.location),
                order: 5,
                fieldType: '',
                formatValue: (val, isOld) =>
                    changeRequest ? (
                        getLocationValue(
                            val as NestedLocation,
                            changeRequest,
                            isOld,
                        )
                    ) : (
                        <></>
                    ),
            },
            new_location_accuracy: {
                label: formatMessage(MESSAGES.accuracy),
                order: 6,
                fieldType: '',
                formatValue: val => <span>{val.toString()}</span>,
            },
            new_opening_date: {
                label: formatMessage(MESSAGES.openingDate),
                order: 7,
                fieldType: '',
                formatValue: val => <span>{moment(val).format('L')}</span>,
            },
            new_closed_date: {
                label: formatMessage(MESSAGES.closingDate),
                order: 8,
                fieldType: '',
                formatValue: val => <span>{moment(val).format('L')}</span>,
            },
            new_reference_instances: {
                label: formatMessage(MESSAGES.multiReferenceInstancesLabel),
                order: 9,
                fieldType: '',
                formatValue: val => (
                    <ReferenceInstances
                        instances={val as InstanceForChangeRequest[]}
                    />
                ),
            },
        }),
        [changeRequest, formatMessage],
    );
    const getValues = useCallback(
        (
            key: string,
            value: any,
        ): {
            oldValue: ReactElement | Optional<Nullable<string>>;
            newValue: ReactElement | Optional<Nullable<string>>;
            isChanged: boolean;
        } => {
            const fieldDef = fieldDefinitions[`new_${key}`];

            if (!changeRequest) {
                return {
                    oldValue: PlaceholderValue,
                    newValue: PlaceholderValue,
                    isChanged: BooleanValue(value),
                };
            }

            const requestedFields = changeRequest.requested_fields;

            const isChanged = requestedFields.includes(`new_${key}`);

            // This will not work if we have to show fields with boolean values
            const newValue = computeNewValue(
                key,
                changeRequest,
                fieldDef,
                isChanged,
            );

            const oldValue = changeRequest[`old_${key}`]
                ? fieldDef.formatValue(changeRequest[`old_${key}`], true)
                : getPlaceholderValue(key);

            return {
                oldValue,
                newValue,
                isChanged,
            };
        },
        [changeRequest, fieldDefinitions],
    );
    useEffect(() => {
        if (!changeRequest) {
            setFields([]);
            return;
        }
        const newFields = orderBy(
            Object.entries(changeRequest)
                .filter(([key]) => fieldDefinitions[key]) // Filter entries that are defined in fieldDefinitions
                .map(([key, value]) => {
                    const fieldKey = key.replace('new_', '');
                    const fieldDef = fieldDefinitions[key];
                    const { oldValue, newValue, isChanged } = getValues(
                        fieldKey,
                        value,
                    );
                    const { label, order, fieldType } = fieldDef;
                    return {
                        key: fieldKey,
                        label,
                        isChanged,
                        isSelected: false,
                        newValue,
                        oldValue,
                        order,
                        fieldType,
                    };
                }),
            ['order'],
            ['asc'],
        );

        setFields(newFields);
    }, [changeRequest, fieldDefinitions, getValues]);

    const setSelected = key => {
        setFields(currentFields =>
            currentFields.map(field =>
                field.key === key
                    ? { ...field, isSelected: !field.isSelected }
                    : field,
            ),
        );
    };
    return { newFields: fields, setSelected };
};
