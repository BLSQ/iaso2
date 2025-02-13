import React from 'react';
import { Box } from '@mui/material';
import { makeStyles } from '@mui/styles';
import {
    LoadingSpinner,
    commonStyles,
    Table,
    AddButton,
    useSafeIntl,
    useRedirectTo,
} from 'bluesquare-components';
import TopBar from '../../../components/nav/TopBarComponent';
import { Filters } from './components/Filters';
import GroupsDialog from './components/GroupsDialog';
import tableColumns from './config';
import MESSAGES from './messages';
import { useGetGroups, useSaveGroups, useDeleteGroups } from './hooks/requests';
import { baseUrls } from '../../../constants/urls';
import { useParamsObject } from '../../../routing/hooks/useParamsObject.tsx';

const useStyles = makeStyles(theme => ({
    ...commonStyles(theme),
}));
const baseUrl = baseUrls.groups;
const Groups = () => {
    const params = useParamsObject(baseUrl);
    const redirectTo = useRedirectTo();
    const classes = useStyles();
    const { formatMessage } = useSafeIntl();

    const { data, isFetching } = useGetGroups(params);
    const { mutate: deleteGroup, isLoading: deleting } = useDeleteGroups();
    const { mutateAsync: saveGroup, isLoading: saving } = useSaveGroups();

    const isLoading = isFetching || deleting || saving;
    return (
        <>
            {isLoading && <LoadingSpinner />}
            <TopBar
                title={formatMessage(MESSAGES.groups)}
                displayBackButton={false}
            />
            <Box className={classes.containerFullHeightNoTabPadded}>
                <Filters params={params} />
                <Box
                    mt={1}
                    mp={2}
                    display="flex"
                    justifyContent="flex-end"
                    alignItems="end"
                >
                    <GroupsDialog
                        saveGroup={saveGroup}
                        titleMessage={MESSAGES.create}
                        renderTrigger={({ openDialog }) => (
                            <AddButton
                                dataTestId="add-group-button"
                                onClick={openDialog}
                            />
                        )}
                        params={params}
                    />
                </Box>

                <Table
                    data={data?.groups ?? []}
                    pages={data?.pages ?? 1}
                    defaultSorted={[{ id: 'name', desc: false }]}
                    columns={tableColumns(
                        formatMessage,
                        params,
                        deleteGroup,
                        saveGroup,
                    )}
                    count={data?.count ?? 0}
                    baseUrl={baseUrl}
                    params={params}
                    redirectTo={(_, newParams) =>
                        redirectTo(baseUrl, newParams)
                    }
                    marginTop={false}
                />
            </Box>
        </>
    );
};

export default Groups;
