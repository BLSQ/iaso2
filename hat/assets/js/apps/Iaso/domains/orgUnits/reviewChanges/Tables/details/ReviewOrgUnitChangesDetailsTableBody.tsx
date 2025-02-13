import React, { FunctionComponent } from 'react';
import { TableBody } from '@mui/material';
import { HighlightFields } from '../../Components/HighlightFieldsChanges';
import { NewOrgUnitField } from '../../hooks/useNewFields';
import { OrgUnitChangeRequestDetails } from '../../types';

type Props = {
    newFields: NewOrgUnitField[];
    setSelected: (key: string) => void;
    isFetchingChangeRequest: boolean;
    changeRequest?: OrgUnitChangeRequestDetails;
    isNew: boolean;
    isNewOrgUnit: boolean;
};

export const ReviewOrgUnitChangesDetailsTableBody: FunctionComponent<Props> = ({
    newFields,
    setSelected,
    isFetchingChangeRequest,
    changeRequest,
    isNew,
    isNewOrgUnit,
}) => {
    return (
        <TableBody>
            {newFields.map(field => {
                const { fieldType, key } = field;
                const changedFieldWithNewValues =
                    changeRequest && changeRequest[`new_${field.key}`];
                const changedFieldWithOldValues =
                    changeRequest && changeRequest[`old_${field.key}`];
                return (
                    <HighlightFields
                        key={key}
                        field={field}
                        newFieldValues={changedFieldWithNewValues}
                        oldFieldValues={changedFieldWithOldValues}
                        status={changeRequest?.status || ''}
                        isNew={isNew}
                        isNewOrgUnit={isNewOrgUnit}
                        setSelected={setSelected}
                        fieldType={fieldType}
                        changeRequest={changeRequest}
                        isFetchingChangeRequest={isFetchingChangeRequest}
                    />
                );
            })}
        </TableBody>
    );
};
