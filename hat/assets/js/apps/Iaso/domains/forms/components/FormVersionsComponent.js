import React from 'react';
import PropTypes from 'prop-types';
import { Box, Button } from '@mui/material';
import {
    useSafeIntl,
    AddButton as AddButtonComponent,
} from 'bluesquare-components';
import { fetchList } from '../../../utils/requests';

import SingleTable from '../../../components/tables/SingleTable';
import FormVersionsDialog from './FormVersionsDialogComponent';

import { baseUrls } from '../../../constants/urls';

import { formVersionsTableColumns } from '../config';
import MESSAGES from '../messages';
import { PERIOD_TYPE_DAY } from '../../periods/constants';

const TEMPLATE_URL = `${
    window.STATIC_URL ?? '/static/'
}templates/XLSForm_Template.xlsx`;

const baseUrl = baseUrls.formDetail;
const defaultOrder = 'version_id';
const FormVersionsComponent = ({
    forceRefresh,
    setForceRefresh,
    periodType,
    formId,
}) => {
    const { formatMessage } = useSafeIntl();
    if (!formId) return null;

    return (
        <Box>
            <Box
                mb={2}
                justifyContent="flex-end"
                alignItems="center"
                display="flex"
            >
                <Button
                    sx={{ mr: 2 }}
                    variant="outlined"
                    href={TEMPLATE_URL}
                    target="_blank"
                    download
                >
                    {formatMessage(MESSAGES.downloadTemplate)}
                </Button>
                <FormVersionsDialog
                    formId={formId}
                    periodType={periodType}
                    titleMessage={MESSAGES.createFormVersion}
                    renderTrigger={({ openDialog }) => (
                        <AddButtonComponent
                            onClick={openDialog}
                            message={MESSAGES.createFormVersion}
                        />
                    )}
                    onConfirmed={() => setForceRefresh(true)}
                />
            </Box>
            <SingleTable
                isFullHeight={false}
                baseUrl={baseUrl}
                endPointPath="formversions"
                exportButtons={false}
                dataKey="form_versions"
                defaultPageSize={20}
                fetchItems={(d, url, signal) =>
                    fetchList(
                        d,
                        `${url}&form_id=${formId}`,
                        'fetchFormVersionsError',
                        'form versions',
                        signal,
                    )
                }
                defaultSorted={[{ id: defaultOrder, desc: true }]}
                columns={formVersionsTableColumns(
                    formatMessage,
                    setForceRefresh,
                    formId,
                    periodType,
                )}
                forceRefresh={forceRefresh}
                onForceRefreshDone={() => setForceRefresh(false)}
            />
        </Box>
    );
};

FormVersionsComponent.defaultProps = {
    periodType: PERIOD_TYPE_DAY,
    setForceRefresh: () => null,
    forceRefresh: false,
    formId: null,
};

FormVersionsComponent.propTypes = {
    periodType: PropTypes.string,
    forceRefresh: PropTypes.bool,
    setForceRefresh: PropTypes.func,
    formId: PropTypes.number,
};

export default FormVersionsComponent;
