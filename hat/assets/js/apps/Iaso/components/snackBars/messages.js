import { defineMessages } from 'react-intl';

const MESSAGES = defineMessages({
    close: {
        id: 'iaso.label.close',
        defaultMessage: 'Close',
    },
    copyError: {
        id: 'iaso.snackBar.copyError',
        defaultMessage: 'Copy error',
    },
    successful: {
        id: 'iaso.snackBar.successful',
        defaultMessage: 'Saved successfully',
    },
    error: {
        id: 'iaso.snackBar.error',
        defaultMessage: 'An error occurred while saving',
    },
    reload: {
        id: 'iaso.snackBar.reload',
        defaultMessage: 'Reload',
    },
    reloadPage: {
        id: 'iaso.snackBar.reloadPage',
        defaultMessage: 'A new version is available! Refresh the page.',
    },
    delete_successful: {
        id: 'iaso.snackBar.delete_successful',
        defaultMessage: 'Deleted successfully',
    },
    fetchFormError: {
        id: 'iaso.snackBar.fetchFormError',
        defaultMessage: 'An error occurred while fetching form detail',
    },
    fetchFormsError: {
        id: 'iaso.snackBar.fetchFormsError',
        defaultMessage: 'An error occurred while fetching forms list',
    },
    fetchOrgUnitError: {
        id: 'iaso.snackBar.fetchOrgUnitError',
        defaultMessage: 'An error occurred while fetching org unit detail',
    },
    fetchInstanceLocationError: {
        id: 'iaso.snackBar.fetchInstanceLocationError',
        defaultMessage: 'An error occurred while fetching instances locations',
    },
    fetchInstanceDictError: {
        id: 'iaso.snackBar.fetchInstanceDictError',
        defaultMessage: 'An error occurred while fetching instances list',
    },
    fetchEnketoError: {
        id: 'iaso.snackBar.fetchEnketoError',
        defaultMessage:
            'Failed to upload to enketo, either the submission is currently edited or enketo is not available',
    },
    fetchSourcesError: {
        id: 'iaso.snackBar.fetchSourcesError',
        defaultMessage: 'An error occurred while fetching sources list',
    },
    fetchGroupsError: {
        id: 'iaso.snackBar.fetchGroupsError',
        defaultMessage: 'An error occurred while fetching groups list',
    },
    saveOrgUnitError: {
        id: 'iaso.snackBar.saveOrgUnitError',
        defaultMessage: 'An error occurred while saving org unit',
    },
    saveOrgUnitSuccesfull: {
        id: 'iaso.snackBar.saveOrgUnitSuccesfull',
        defaultMessage: 'Org unit saved successfully',
    },
    fetchOrgUnitTypesError: {
        id: 'iaso.snackBar.fetchOrgUnitTypesError',
        defaultMessage: 'An error occurred while fetching org unit types list',
    },
    saveOrgUnitTypeSuccesfull: {
        id: 'iaso.snackBar.saveOrgUnitTypeSuccesfull',
        defaultMessage: 'Org unit type saved successfully',
    },
    saveOrgUnitTypeError: {
        id: 'iaso.snackBar.saveOrgUnitTypeError',
        defaultMessage: 'An error occurred while saving org unit type',
    },
    deleteOrgUnitTypeSuccesfull: {
        id: 'iaso.snackBar.deleteOrgUnitTypeSuccesfull',
        defaultMessage: 'Org unit type deleted successfully',
    },
    deleteOrgUnitTypeError: {
        id: 'iaso.snackBar.deleteOrgUnitTypeError',
        defaultMessage: 'An error occurred while deleting org unit type',
    },
    fetchOrgUnitsError: {
        id: 'iaso.snackBar.fetchOrgUnitsError',
        defaultMessage: 'An error occurred while fetching org unit list',
    },
    fetchLogDetailError: {
        id: 'iaso.snackBar.fetchLogDetailError',
        defaultMessage: 'An error occurred while fetching log detail',
    },
    fetchDevicesError: {
        id: 'iaso.snackBar.fetchDevicesError',
        defaultMessage: 'An error occurred while fetching devices list',
    },
    fetchInstanceError: {
        id: 'iaso.snackBar.fetchInstanceError',
        defaultMessage: 'An error occurred while fetching instance detail',
    },
    assignInstanceError: {
        id: 'iaso.snackBar.assignInstanceError',
        defaultMessage: 'An error occured while saving the instance',
    },
    restoreInstanceError: {
        id: 'iaso.snackBar.restoreInstanceError',
        defaultMessage: 'An error occured while restoring the instance',
    },
    createExportRequestErrorNothingToExportError: {
        id: 'iaso.snackBar.createExportRequestErrorNothingToExportError',
        defaultMessage:
            'We found nothing to export, change your filter or force the re-export',
    },
    createExportRequestErrorNoVersionError: {
        id: 'iaso.snackBar.createExportRequestErrorNoVersionError',
        defaultMessage: 'One of the instance had no version specified',
    },
    createExportRequestErrorNoFormMappingError: {
        id: 'iaso.snackBar.createExportRequestErrorNoFormMappingError',
        defaultMessage: "The form doesn't a form mapping to export to dhis2",
    },
    createExportRequestErrorNotSupportedError: {
        id: 'iaso.snackBar.createExportRequestErrorNotSupportedError',
        defaultMessage: "Forcing export isn't supported for event tracker",
    },
    createExportRequestError: {
        id: 'iaso.snackBar.createExportRequestError',
        defaultMessage: 'An error occured while creating export request',
    },
    createExportRequestSuccess: {
        id: 'iaso.snackBar.createExportRequestSuccess',
        defaultMessage: 'Export request queued',
    },
    saveLinkError: {
        id: 'iaso.snackBar.saveLinkError',
        defaultMessage: 'An error occurred while saving link',
    },
    fetchProfilesError: {
        id: 'iaso.snackBar.fetchProfilesError',
        defaultMessage: 'An error occurred while fetching profiles list',
    },
    fetchLinksError: {
        id: 'iaso.snackBar.fetchLinksError',
        defaultMessage: 'An error occurred while fetching links list',
    },
    fetchAlgorithmsError: {
        id: 'iaso.snackBar.fetchAlgorithmsError',
        defaultMessage: 'An error occurred while fetching algorithms list',
    },
    locationLimitWarning: {
        id: 'iaso.snackBar.locationLimitWarning',
        defaultMessage:
            'Display too much items on the map can reduce the performance',
    },
    fetchLinkDetailError: {
        id: 'iaso.snackBar.fetchLinkDetailError',
        defaultMessage: 'An error occurred while fetching link detail',
    },
    deleteRun: {
        id: 'iaso.snackBar.deleteRun',
        defaultMessage: 'An error occurred while deleting algorithms run',
    },
    fetchPeriodsError: {
        id: 'iaso.snackBar.fetchPeriodsError',
        defaultMessage: 'An error occurred while fetching periods list',
    },
    fetchProjectsError: {
        id: 'iaso.snackBar.fetchProjectsError',
        defaultMessage: 'An error occurred while fetching projects list',
    },
    createFormError: {
        id: 'iaso.snackBar.createFormError',
        defaultMessage: 'An error occurred while creating a form',
    },
    createFormVersionError: {
        id: 'iaso.snackBar.createFormVersionError',
        defaultMessage: 'An error occurred while creating a form version',
    },
    updateFormVersionError: {
        id: 'iaso.snackBar.updateFormVersionError',
        defaultMessage: 'An error occurred while updating a form version',
    },
    updateFormError: {
        id: 'iaso.snackBar.updateFormError',
        defaultMessage: 'An error occurred while updating a form',
    },
    deleteFormError: {
        id: 'iaso.snackBar.deleteFormError',
        defaultMessage: 'An error occurred while deleting a form',
    },
    fetchCompletenessError: {
        id: 'iaso.snackBar.fetchCompletenessError',
        defaultMessage: 'An error occured while fetching completness',
    },
    generateDerivedRequestSuccess: {
        id: 'iaso.snackBar.generateDerivedRequestSuccess',
        defaultMessage: 'Generation scheduled',
    },
    generateDerivedRequestError: {
        id: 'iaso.snackBar.generateDerivedRequestError',
        defaultMessage: 'Generation failed',
    },
    noInstancesOnMap: {
        defaultMessage: 'Cannot find an instance with geolocation',
        id: 'iaso.instance.missingGeolocation',
    },
    saveUserSuccessful: {
        defaultMessage: 'User saved',
        id: 'iaso.snackBar.saveUserSuccessful',
    },
    saveUserError: {
        defaultMessage: 'An error occurred while saving user profile',
        id: 'iaso.snackBar.saveUserError',
    },
    deleteUserSuccessful: {
        defaultMessage: 'User deleted',
        id: 'iaso.snackBar.deleteUserSuccessful',
    },
    deleteUserError: {
        defaultMessage: 'An error occurred while deleting user profile',
        id: 'iaso.snackBar.deleteUserError',
    },
    saveGroupSuccesfull: {
        defaultMessage: 'Group saved',
        id: 'iaso.snackBar.saveGroupSuccesfull',
    },
    saveGroupError: {
        defaultMessage: 'An error occurred while saving group',
        id: 'iaso.snackBar.saveGroupError',
    },
    saveMultiEditOrgUnitsSuccesfull: {
        defaultMessage: 'Selected org unit saved successfully',
        id: 'iaso.snackBar.saveMultiEditOrgUnitsSuccesfull',
    },
    saveMultiEditOrgUnitsLaunched: {
        defaultMessage:
            'The modifications to the org units will take a few minutes to take effect',
        id: 'iaso.snackBar.saveMultiEditOrgUnitsLaunched',
    },
    saveMultiEditOrgUnitsError: {
        defaultMessage: 'An error occurred while saving selected org units',
        id: 'iaso.snackBar.saveMultiEditOrgUnitsError',
    },
    deleteGroupSuccesfull: {
        defaultMessage: 'Group deleted',
        id: 'iaso.snackBar.deleteGroupSuccesfull',
    },
    deleteGroupError: {
        defaultMessage: 'An error occurred while deleting group',
        id: 'iaso.snackBar.deleteGroupError',
    },

    patchTaskError: {
        defaultMessage: 'An error occurred while updating the task',
        id: 'iaso.snackBar.patchTaskError',
    },
    patchTaskSuccess: {
        defaultMessage: 'The task has been updated.',
        id: 'iaso.snackBar.patchTaskSuccess',
    },
    createDataSourceError: {
        defaultMessage: 'Error creating the data source',
        id: 'iaso.snackBar.createDataSourceError',
    },
    updateDataSourceError: {
        defaultMessage: 'Error updating the data source',
        id: 'iaso.snackBar.updateDataSourceError',
    },
    updateDefaultSourceError: {
        defaultMessage: 'Error updating the default source',
        id: 'iaso.snackBar.updateDefaultSourceError',
    },
    fetchFormVersionsError: {
        id: 'iaso.snackBar.fetchFormVersionsError',
        defaultMessage: 'An error occurred while fetching form versions',
    },
    fetchLogsError: {
        id: 'iaso.snackBar.fetchLogsError',
        defaultMessage: 'An error occurred while fetching logs',
    },
    fetchMappingsError: {
        id: 'iaso.snackBar.fetchMappingsError',
        defaultMessage: 'An error occurred while fetching mappings',
    },
    retrieveTaskError: {
        id: 'iaso.snackBar.retrieveTaskError',
        defaultMessage: 'An error occurred while fetching task',
    },
    generateCSVError: {
        id: 'iaso.snackBar.generateCSVError',
        defaultMessage: 'An error occurred while generating CSV file',
    },
    getRootDataError: {
        id: 'iaso.snackBar.getRootDataError',
        defaultMessage: 'An error occurred while fetching Treeview items',
    },
    getChildrenDataError: {
        id: 'iaso.snackBar.getChildrenDataError',
        defaultMessage:
            'An error occurred while fetching Treeview item children',
    },
    searchOrgUnitsError: {
        id: 'iaso.snackBar.searchOrgUnitsError',
        defaultMessage: 'An error occurred while searching org units',
    },
    goToEntity: {
        id: 'iaso.snackBar.goToEntity',
        defaultMessage: 'Go to entity',
    },
    completenessMapWarning: {
        defaultMessage: 'Org unit(s) without geolocation found',
        id: 'iaso.completenessStats.completenessMapWarning',
    },
    logoutError: {
        id: 'iaso.snackBar.logoutError',
        defaultMessage: 'An error occurred while logging out',
    },
});

export default MESSAGES;
