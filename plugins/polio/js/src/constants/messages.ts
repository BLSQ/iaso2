import { defineMessages } from 'react-intl';

const MESSAGES = defineMessages({
    account: {
        id: 'iaso.label.account',
        defaultMessage: 'Account ID',
    },
    geojson: {
        id: 'iaso.polio.label.geojson',
        defaultMessage: 'Geojson',
    },
    noGeojson: {
        id: 'iaso.label.hasNoGeometryAndGps',
        defaultMessage: 'Without geographic data',
    },
    selectOrgUnit: {
        id: 'iaso.polio.label.selectOrgUnit',
        defaultMessage: 'Select intial region',
    },
    polio: {
        defaultMessage: 'Polio',
        id: 'iaso.label.polio',
    },
    scope_per_round: {
        defaultMessage: 'Separate scope per round',
        id: 'iaso.polio.label.scope_per_round',
    },
    source_version: {
        id: 'iaso.groups.sourceVersion',
        defaultMessage: 'Source version',
    },
    infos: {
        defaultMessage: 'Infos',
        id: 'iaso.label.infos',
    },
    scopes: {
        defaultMessage: 'Scopes',
        id: 'iaso.polio.label.scopes',
    },
    separate_scopes_per_round: {
        defaultMessage: 'Separate scope per round',
        id: 'iaso.polio.label.scope_per_round',
    },
    preparedness_spreadsheet_url: {
        defaultMessage: 'Preparedness spreadsheet url',
        id: 'iaso.polio.label.preparednesSpreadsheetUrl',
    },
    preparedness_sync_status: {
        defaultMessage: 'Preparedness status',
        id: 'iaso.polio.label.preparednesSyncStatus',
    },
    preparednessSomeWarningsDuringTheParsing: {
        defaultMessage:
            'Warning the application encountered problems while parsing the preparedness sheet',
        id: 'iaso.polio.label.preparednessSomeWarningsDuringTheParsing',
    },
    helpTextEditVaccineViaScope: {
        defaultMessage: 'The list of vaccines comes from the scope',
        id: 'iaso.polio.label.helpTextEditVaccineViaScope',
    },
    org_units: {
        defaultMessage: 'Org units',
        id: 'iaso.label.orgUnit',
    },
    campaigns: {
        defaultMessage: 'Campaigns',
        id: 'iaso.polio.label.campaigns',
    },
    campaign: {
        defaultMessage: 'Campaign',
        id: 'iaso.polio.label.campaign',
    },
    delete: {
        id: 'iaso.label.delete',
        defaultMessage: 'Delete',
    },
    edit: {
        id: 'iaso.label.edit',
        defaultMessage: 'Edit',
    },
    removeDistrict: {
        defaultMessage: 'Unselect district',
        id: 'iaso.polio.button.label.removeDistrict',
    },
    removeRegion: {
        defaultMessage: 'Unselect region',
        id: 'iaso.polio.button.label.removeRegion',
    },
    addDistrict: {
        defaultMessage: 'Select district',
        id: 'iaso.polio.button.label.addDistrict',
    },
    addRegion: {
        defaultMessage: 'Select region',
        id: 'iaso.polio.button.label.addRegion',
    },
    addAuthorisation: {
        defaultMessage: 'Add authorisation',
        id: 'iaso.polio.button.label.addAuthorisation',
    },
    confirm: {
        defaultMessage: 'Confirm',
        id: 'iaso.label.confirm',
    },
    cancel: {
        defaultMessage: 'Cancel',
        id: 'iaso.label.cancel',
    },
    configuration: {
        defaultMessage: 'Configuration',
        id: 'iaso.polio.label.configuration',
    },
    configEmailNotif: {
        defaultMessage: 'Configure country: {country}',
        id: 'iaso.polio.label.configEmailNotif',
    },
    selectUsers: {
        id: 'iaso.polio.select.label.selectUsers',
        defaultMessage: 'Select users',
    },
    selectLanguage: {
        id: 'iaso.polio.select.label.selectLanguage',
        defaultMessage: 'Select language',
    },
    country: {
        id: 'iaso.polio.table.label.country',
        defaultMessage: 'Country',
    },
    usersToNotify: {
        id: 'iaso.polio.table.label.usersToNotify',
        defaultMessage: 'Users to notify',
    },
    language: {
        id: 'iaso.polio.table.label.language',
        defaultMessage: 'Language',
    },
    actions: {
        id: 'iaso.polio.table.label.actions',
        defaultMessage: 'Actions',
    },
    calendar: {
        id: 'iaso.polio.calendar',
        defaultMessage: 'Calendar',
    },
    calendarPdfTitle: {
        id: 'iaso.polio.calendar.pdf.title',
        defaultMessage: 'Campaigns Calendar',
    },
    weeks: {
        id: 'iaso.polio.calendar.weeks',
        defaultMessage: 'week(s)',
    },
    weeksShort: {
        id: 'iaso.polio.calendar.weeksShort',
        defaultMessage: 'w.',
    },
    startDate: {
        id: 'iaso.label.dateFrom',
        defaultMessage: 'Start date',
    },
    started_at: {
        id: 'iaso.label.dateFrom',
        defaultMessage: 'Start date',
    },
    endDate: {
        id: 'iaso.label.dateTo',
        defaultMessage: 'End date',
    },
    source_ref: {
        defaultMessage: 'Source ref',
        id: 'iaso.orgUnits.sourceRef',
    },
    ended_at: {
        id: 'iaso.label.dateTo',
        defaultMessage: 'End date',
    },
    name: {
        id: 'iaso.polio.label.name',
        defaultMessage: 'Name',
    },
    r1StartDate: {
        id: 'iaso.polio.calendar.r1StartDate',
        defaultMessage: 'R1 date',
    },
    raStatus: {
        id: 'iaso.polio.raStatus',
        defaultMessage: 'R1 date',
    },
    budgetStatus: {
        id: 'iaso.polio.budgetStatus',
        defaultMessage: 'Budget status',
    },
    budget_status: {
        id: 'iaso.polio.budgetStatus',
        defaultMessage: 'Budget status',
    },
    vaccine: {
        id: 'iaso.polio.vaccine',
        defaultMessage: 'Vaccine',
    },
    vaccine_name: {
        id: 'iaso.polio.vaccine',
        defaultMessage: 'Vaccine',
    },
    vaccines: {
        id: 'iaso.polio.vaccines',
        defaultMessage: 'Vaccines',
    },
    endDateBeforeStartDate: {
        id: 'iaso.polio.form.validator.error.endDateBeforeStartDate',
        defaultMessage: "End date can't be before start date",
    },
    startDateAfterEndDate: {
        id: 'iaso.polio.form.validator.error.startDateAfterEndDate',
        defaultMessage: "Start date can't be after end date",
    },
    startDateBeforePreviousEndDate: {
        id: 'iaso.polio.form.validator.error.startDateBeforePreviousEndDate',
        defaultMessage:
            "Start date can't be before or equal previous round end date",
    },
    endDateAfterNextStartDate: {
        id: 'iaso.polio.form.validator.error.endDateAfterNextStartDate',
        defaultMessage:
            "End date can't be after or equal next round start date",
    },
    positiveInteger: {
        id: 'iaso.polio.form.validator.error.positiveInteger',
        defaultMessage: 'Please use a positive integer',
    },
    positiveRangeInteger: {
        id: 'iaso.polio.form.validator.error.positiveRangeInteger',
        defaultMessage: 'Please use a positive integer between 0 and 100',
    },
    positiveNumber: {
        id: 'iaso.polio.form.validator.error.positiveNumber',
        defaultMessage: 'Please use a positive number',
    },
    noCampaign: {
        id: 'iaso.polio.noCampaign',
        defaultMessage: 'No campaign to display',
    },
    // Start
    epid: {
        id: 'iaso.polio.form.label.epid',
        defaultMessage: 'EPID',
    },
    campaignIdentifier: {
        id: 'iaso.polio.form.label.campaignIdentifier',
        defaultMessage: 'Campaign identifier',
    },
    obrName: {
        id: 'iaso.polio.form.label.obrName',
        defaultMessage: 'OBR Name',
    },
    obr_name: {
        id: 'iaso.polio.form.label.obrName',
        defaultMessage: 'OBR Name',
    },
    virus: {
        id: 'iaso.polio.form.label.virus',
        defaultMessage: 'Virus',
    },
    description: {
        id: 'iaso.polio.form.label.description',
        defaultMessage: 'Description',
    },
    responsibleOfficer: {
        id: 'iaso.polio.form.label.responsibleOfficer',
        defaultMessage: 'Responsible officer',
    },
    gpeiCoordinator: {
        id: 'iaso.polio.form.label.gpeiCoordinator',
        defaultMessage: 'GPEI Coordinator',
    },
    gpei_coordinator: {
        id: 'iaso.polio.form.label.gpeiCoordinator',
        defaultMessage: 'GPEI Coordinator',
    },
    preventive: {
        id: 'iaso.polio.form.label.preventive',
        defaultMessage: 'Preventive campaign',
    },
    is_preventive: {
        id: 'iaso.polio.form.label.preventive',
        defaultMessage: 'Preventive campaign',
    },
    preventiveShort: {
        id: 'iaso.polio.form.label.preventive.short',
        defaultMessage: 'Preventive',
    },
    dateOfOnset: {
        id: 'iaso.polio.form.label.dateOfOnset',
        defaultMessage: 'Date of onset',
    },
    onset_at: {
        id: 'iaso.polio.form.label.dateOfOnset',
        defaultMessage: 'Date of onset',
    },
    virusNotificationDate: {
        id: 'iaso.polio.form.label.virusNotificationDate',
        defaultMessage: 'Virus notification date',
    },
    cvdpv2_notified_at: {
        id: 'iaso.polio.form.label.virusNotificationDate',
        defaultMessage: 'Virus notification date',
    },
    outbreakdeclarationdate: {
        id: 'iaso.polio.form.label.outbreakdeclarationdate',
        defaultMessage: 'Outbreak declaration date',
    },
    outbreak_declaration_date: {
        id: 'iaso.polio.form.label.outbreakdeclarationdate',
        defaultMessage: 'Outbreak declaration date',
    },
    verificationScore: {
        id: 'iaso.polio.form.label.verificationScore',
        defaultMessage: 'Verification Score (/20)',
    },
    fieldInvestigationDate: {
        id: 'iaso.polio.form.label.fieldInvestigationDate',
        defaultMessage: 'Field Investigation Date',
    },
    investigation_at: {
        id: 'iaso.polio.form.label.fieldInvestigationDate',
        defaultMessage: 'Field Investigation Date',
    },
    risk_assessment_first_draft_submitted_at: {
        id: 'iaso.polio.form.label.risk_assessment_first_draft_submitted_at',
        defaultMessage: '1st Draft Submission',
    },
    detection_first_draft_submitted_at: {
        id: 'iaso.polio.form.label.risk_assessment_first_draft_submitted_at',
        defaultMessage: '1st Draft Submission',
    },
    detection_responsible: {
        id: 'iaso.polio.label.detection_responsible',
        defaultMessage: 'Detection responsible',
    },
    ag_nopv_group_met_at: {
        id: 'iaso.polio.form.label.agNopvGroup',
        defaultMessage: 'AG/nOPV Group',
    },
    dgAuthorization: {
        id: 'iaso.polio.form.label.dgAuthorization',
        defaultMessage: 'DG Authorization',
    },
    dg_authorized_at: {
        id: 'iaso.polio.form.label.dgAuthorization',
        defaultMessage: 'DG Authorization',
    },
    target_population: {
        id: 'iaso.polio.form.label.targetpopulation',
        defaultMessage: 'Target population Round',
    },
    targetPopulation: {
        id: 'iaso.polio.label.targetPopulation',
        defaultMessage: 'Target population',
    },
    percentage_covered_target_population: {
        id: 'iaso.polio.form.label.percentageCoveredTargetPopulation',
        defaultMessage: 'Percentage covered target population',
    },
    dosesRequested: {
        id: 'iaso.polio.form.label.dosesRequested',
        defaultMessage: 'Doses Requested',
    },
    doses_requested: {
        id: 'iaso.polio.form.label.dosesRequested',
        defaultMessage: 'Doses Requested',
    },
    region: {
        id: 'iaso.polio.table.label.region',
        defaultMessage: 'Region',
    },
    district: {
        id: 'iaso.polio.district',
        defaultMessage: 'District',
    },
    districts: {
        id: 'iaso.polio.districts',
        defaultMessage: 'Districts',
    },
    selectRegion: {
        id: 'iaso.polio.table.label.selectRegion',
        defaultMessage: 'Select region',
    },
    refreshing: {
        id: 'iaso.polio.table.label.refreshing',
        defaultMessage: 'Refreshing...',
    },
    pleaseSaveCampaign: {
        id: 'iaso.polio.form.label.pleaseSaveCampaign',
        defaultMessage: 'Please save the Campaign before selecting scope.',
    },
    who_disbursed_to_co_at: {
        id: 'iaso.polio.form.label.disbursedToCoWho',
        defaultMessage: 'Disbursed to CO (WHO)',
    },
    who_disbursed_to_moh_at: {
        id: 'iaso.polio.form.label.disbursedToMohWho',
        defaultMessage: 'Disbursed to MOH (WHO)',
    },
    unicef_disbursed_to_co_at: {
        id: 'iaso.polio.form.label.disbursedToCoUnicef',
        defaultMessage: 'Disbursed to CO (Unicef)',
    },
    unicef_disbursed_to_moh_at: {
        id: 'iaso.polio.form.label.disbursedToMohUnicef',
        defaultMessage: 'Disbursed to MOH (Unicef)',
    },
    mop_up_started_at: {
        id: 'iaso.polio.form.label.mopUpStart',
        defaultMessage: 'Mop Up Start',
    },
    mop_up_ended_at: {
        id: 'iaso.polio.form.label.mopUpEnd',
        defaultMessage: 'Mop Up End',
    },
    im_started_at: {
        id: 'iaso.polio.form.label.imStart',
        defaultMessage: 'IM Start',
    },
    im_ended_at: {
        id: 'iaso.polio.form.label.imEnd',
        defaultMessage: 'IM End',
    },
    lqas_started_at: {
        id: 'iaso.polio.form.label.lqasStart',
        defaultMessage: 'LQAS Start',
    },
    lqas_ended_at: {
        id: 'iaso.polio.form.label.lqasEnd',
        defaultMessage: 'LQAS End',
    },
    lqas_district_passing: {
        id: 'iaso.polio.form.label.districtsPassingLqas',
        defaultMessage: 'Districts passing LQAS',
    },
    lqas_district_failing: {
        id: 'iaso.polio.form.label.districtsFailingLqas',
        defaultMessage: 'Districts failing LQAS',
    },
    main_awareness_problem: {
        id: 'iaso.polio.form.label.mainReasonForNonVaccination',
        defaultMessage: 'Main reason for non-vaccination',
    },
    im_percentage_children_missed_in_household: {
        id: 'iaso.polio.form.label.ratioChildrenMissedInHousehold',
        defaultMessage: '% children missed IN household',
    },
    im_percentage_children_missed_out_household: {
        id: 'iaso.polio.form.label.ratioChildrenMissedOutOfHousehold',
        defaultMessage: '% children missed OUT OF household',
    },
    im_percentage_children_missed_in_plus_out_household: {
        id: 'iaso.polio.form.label.ratioChildrenMissedInAndOutOfHousehold',
        defaultMessage: '% children missed IN+OUT OF household',
    },
    awareness_of_campaign_planning: {
        id: 'iaso.polio.form.label.awarenessCampaignPlanning',
        defaultMessage: 'Awareness of campaign planning (%)',
    },
    createCampaign: {
        id: 'iaso.polio.createCampaign',
        defaultMessage: 'Create campaign',
    },
    editCampaign: {
        id: 'iaso.polio.editCampaign',
        defaultMessage: 'Edit campaign',
    },
    baseInfo: {
        id: 'iaso.polio.title.baseInfo',
        defaultMessage: 'Base info',
    },
    detection: {
        id: 'iaso.polio.title.detection',
        defaultMessage: 'Detection',
    },
    riskAssessment: {
        id: 'iaso.polio.title.riskAssessment',
        defaultMessage: 'Risk Assessment',
    },
    risk_assessment_status: {
        id: 'iaso.polio.label.risk_assessment_status',
        defaultMessage: 'Risk assessment',
    },
    scope: {
        id: 'iaso.polio.title.scope',
        defaultMessage: 'Scope',
    },
    budget: {
        id: 'iaso.polio.title.budget',
        defaultMessage: 'Budget',
    },
    preparedness: {
        id: 'iaso.polio.title.preparedness',
        defaultMessage: 'Preparedness',
    },
    deleteWarning: {
        id: 'iaso.polio.label.deleteWarning',
        defaultMessage: 'Are you sure you want to delete this campaign?',
    },
    restoreWarning: {
        id: 'iaso.polio.label.restoreWarning',
        defaultMessage: 'Are you sure you want to restore this campaign?',
    },
    no: {
        id: 'iaso.polio.label.no',
        defaultMessage: 'No',
    },
    yes: {
        id: 'iaso.polio.label.yes',
        defaultMessage: 'Yes',
    },
    status: {
        id: 'iaso.polio.table.label.status',
        defaultMessage: 'Status',
    },
    import: {
        id: 'iaso.polio.button.label.import',
        defaultMessage: 'Import',
    },
    create: {
        id: 'iaso.polio.label.create',
        defaultMessage: 'Create',
    },
    csv: {
        id: 'iaso.polio.label.csv',
        defaultMessage: 'CSV',
    },
    enterOrCreateGoogleSheet: {
        id: 'iaso.polio.label.enterOrCreateGoogleSheet',
        defaultMessage:
            'Enter Google Sheet url or use the button to generate a new one',
    },
    enterGoogleSheet: {
        id: 'iaso.polio.label.enterGoogleSheet',
        defaultMessage: 'Enter Google Sheet url',
    },
    preparednessGoogleSheetUrl: {
        id: 'iaso.polio.title.preparednessGoogleSheetUrl',
        defaultMessage: 'Preparedness Google Sheet URL',
    },
    refreshPreparednessData: {
        id: 'iaso.polio.title.refreshPreparednessData',
        defaultMessage: 'Refresh Preparedness data',
    },
    generateSpreadsheet: {
        id: 'iaso.polio.title.generateSpreadsheet',
        defaultMessage: 'Generate a spreadsheet',
    },
    preparednessError: {
        id: 'iaso.polio.label.preparednessError',
        defaultMessage: 'Error Generating preparedness',
    },
    national: {
        id: 'iaso.polio.label.national',
        defaultMessage: 'National',
    },
    regional: {
        id: 'iaso.polio.label.regional',
        defaultMessage: 'Regional',
    },
    districtScore: {
        id: 'iaso.polio.label.districtScore',
        defaultMessage: 'District',
    },
    refreshedAt: {
        id: 'iaso.polio.label.refreshedAt',
        defaultMessage: 'Refreshed at',
    },
    whoToRecruit: {
        id: 'iaso.polio.label.whoToRecruit',
        defaultMessage: 'WHO To Recruit',
    },
    whoCompletedRecruitement: {
        id: 'iaso.polio.label.whoCompletedRecruitement',
        defaultMessage: 'WHO Completed Recruitment',
    },
    unicefToRecruit: {
        id: 'iaso.polio.label.unicefToRecruit',
        defaultMessage: 'UNICEF To Recruit',
    },
    unicefCompletedRecruitement: {
        id: 'iaso.polio.label.unicefCompletedRecruitement',
        defaultMessage: 'UNICEF Completed Recruitment',
    },
    paymentMode: {
        id: 'iaso.polio.label.paymentMode',
        defaultMessage: 'Payment Mode',
    },
    payment_mode: {
        id: 'iaso.polio.label.paymentMode',
        defaultMessage: 'Payment Mode',
    },
    pending: {
        id: 'iaso.polio.label.pending',
        defaultMessage: 'Pending',
    },
    ongoing: {
        id: 'iaso.polio.label.ongoing',
        defaultMessage: 'Ongoing',
    },
    finished: {
        id: 'iaso.polio.label.finished',
        defaultMessage: 'Finished',
    },
    reviewedByRrt: {
        id: 'iaso.polio.label.reviewedByRrt',
        defaultMessage: 'Reviewed by RRT',
    },
    submitted: {
        id: 'iaso.polio.label.submitted',
        defaultMessage: 'Submitted',
    },
    toSubmit: {
        id: 'iaso.polio.label.toSubmit',
        defaultMessage: 'To submit',
    },
    who: {
        id: 'iaso.polio.label.who',
        defaultMessage: 'WHO',
    },
    unicef: {
        id: 'iaso.polio.label.unicef',
        defaultMessage: 'UNICEF',
    },
    moh: {
        id: 'iaso.polio.label.moh',
        defaultMessage: 'MOH',
    },
    provinceOption: {
        id: 'iaso.polio.label.provinceOption',
        defaultMessage: 'PROVINCE',
    },
    PREPARING: {
        id: 'iaso.polio.PREPARING',
        defaultMessage: 'Preparing',
    },
    ROUND1START: {
        id: 'iaso.polio.ROUND1START',
        defaultMessage: 'Round 1 started',
    },
    ROUND1DONE: {
        id: 'iaso.polio.ROUND1DONE',
        defaultMessage: 'Round 1 completed',
    },
    ROUND2START: {
        id: 'iaso.polio.ROUND2START',
        defaultMessage: 'Round 2 started',
    },
    ROUND2DONE: {
        id: 'iaso.polio.ROUND2DONE',
        defaultMessage: 'Round 2 completed',
    },
    filter: {
        id: 'iaso.polio.label.filter',
        defaultMessage: 'Filter',
    },
    RoundStartFrom: {
        id: 'iaso.polio.label.RoundStartFrom',
        defaultMessage: 'Round start date from',
    },
    RoundStartTo: {
        id: 'iaso.polio.label.RoundStartTo',
        defaultMessage: 'Round start date to',
    },
    sortAsc: {
        id: 'iaso.polio.label.sortAsc',
        defaultMessage: 'Sort ascending',
    },
    sortDesc: {
        id: 'iaso.polio.label.sortDesc',
        defaultMessage: 'Sort descending',
    },
    search: {
        id: 'iaso.polio.label.search',
        defaultMessage: 'Search',
    },
    fastPrevious: {
        id: 'iaso.polio.label.calendar.fastPrevious',
        defaultMessage: 'Previous 4 weeks',
    },
    previous: {
        id: 'iaso.polio.label.calendar.previous',
        defaultMessage: 'Previous week',
    },
    next: {
        id: 'iaso.polio.label.calendar.next',
        defaultMessage: 'Next week',
    },
    fastNext: {
        id: 'iaso.polio.label.calendar.fastNext',
        defaultMessage: 'Next 4 weeks',
    },
    selectDate: {
        id: 'iaso.polio.label.calendar.selectDate',
        defaultMessage: 'Select a date',
    },
    clear: {
        id: 'iaso.polio.label.clear',
        defaultMessage: 'Clear',
    },
    lqas: {
        id: 'iaso.polio.label.lqas',
        defaultMessage: 'LQAS',
    },
    childrenChecked: {
        id: 'iaso.polio.label.childrenChecked',
        defaultMessage: 'Children checked',
    },
    childrenMarked: {
        id: 'iaso.polio.label.childrenMarked',
        defaultMessage: 'Children with mark',
    },
    passing: {
        id: 'iaso.polio.label.passed',
        defaultMessage: 'Passed',
    },
    verypoor: {
        id: 'iaso.polio.label.verypoor',
        defaultMessage: 'Very poor',
    },
    poor: {
        id: 'iaso.polio.label.poor',
        defaultMessage: 'Poor',
    },
    moderate: {
        id: 'iaso.polio.label.moderate',
        defaultMessage: 'Moderate',
    },
    countryPassing: {
        id: 'iaso.polio.label.countryPassing',
        defaultMessage: '80% or more districts passed',
    },
    countryFailing: {
        id: 'iaso.polio.label.countryFailing',
        defaultMessage: 'Less than 80% districts passed',
    },
    '1lqasOK': {
        id: 'iaso.polio.label.passed',
        defaultMessage: 'Passed',
    },
    disqualified: {
        id: 'iaso.polio.label.disqualified',
        defaultMessage: 'Disqualified',
    },
    '2lqasDisqualified': {
        id: 'iaso.polio.label.disqualified',
        defaultMessage: 'Disqualified',
    },
    failing: {
        id: 'iaso.polio.label.failed',
        defaultMessage: 'Failed',
    },
    '3lqasFail': {
        id: 'iaso.polio.label.verypoor',
        defaultMessage: 'Very poor',
    },
    '3lqasverypoor': {
        id: 'iaso.polio.label.verypoor',
        defaultMessage: 'Very poor',
    },
    '3lqasmoderate': {
        id: 'iaso.polio.label.moderate',
        defaultMessage: 'Moderate',
    },
    '3lqaspoor': {
        id: 'iaso.polio.label.poor',
        defaultMessage: 'Poor',
    },
    '3lqasoversampled': {
        id: 'iaso.polio.label.oversampled',
        defaultMessage: 'Oversampled',
    },
    '3lqasundersampled': {
        id: 'iaso.polio.label.undersampled',
        defaultMessage: 'Undersampled',
    },
    inScope: {
        id: 'iaso.polio.label.inScope',
        defaultMessage: 'No data found',
    },
    noValidData: {
        id: 'iaso.polio.label.noValidData',
        defaultMessage: 'No valid data',
    },
    districtsNotFound: {
        id: 'iaso.polio.label.districtsNotFound',
        defaultMessage: 'Districts not found',
    },
    districtName: {
        id: 'iaso.polio.label.name',
        defaultMessage: 'Name',
    },
    datesIgnored: {
        id: 'iaso.polio.label.datesIgnored',
        defaultMessage: 'Dates ignored',
    },
    lqasResults: {
        id: 'iaso.polio.label.lqasResults',
        defaultMessage: 'LQAS results',
    },
    im: {
        id: 'iaso.polio.label.im',
        defaultMessage: 'IM',
    },
    '1imOK': {
        id: 'iaso.polio.label.imOK',
        defaultMessage: '>95%',
    },
    '2imWarning': {
        id: 'iaso.polio.label.imWarning',
        defaultMessage: '90%-94%',
    },
    '3imFail': {
        id: 'iaso.polio.label.imFail',
        defaultMessage: '<90%',
    },
    '4imError': {
        id: 'iaso.polio.label.invalidData',
        defaultMessage: 'Invalid data',
    },
    imResults: {
        id: 'iaso.polio.label.imResults',
        defaultMessage: 'IM Results',
    },
    enable_send_weekly_email: {
        id: 'iaso.polio.label.enableSendWeeklyEmail',
        defaultMessage: 'Send a weekly e-mail reminder',
    },
    emailListTooltip: {
        id: 'iaso.polio.label.emailListTooltip',
        defaultMessage: 'Change email list via country configuration',
    },
    emailListEmpty: {
        id: 'iaso.polio.label.emailListEmpty',
        defaultMessage: 'No email configured for this country',
    },
    emailListLabel: {
        id: 'iaso.polio.label.emailListLabel',
        defaultMessage: 'Configured emails :',
    },
    emailNotifyButton: {
        id: 'iaso.polio.label.emailNotifyButton',
        defaultMessage: 'Notify coordinators by e-mail',
    },
    lqasPerRegion: {
        id: 'iaso.polio.label.lqasPerRegion',
        defaultMessage:
            'Districts passing LQAS per region (based on districts found)',
    },
    imPerRegion: {
        id: 'iaso.polio.label.imPerRegion',
        defaultMessage:
            'Vaccination ratio per region (based on districts found)',
    },
    vaccinated: {
        id: 'iaso.polio.label.vaccinated',
        defaultMessage: 'Vaccinated',
    },
    spreadsheetImportTitle: {
        id: 'iaso.polio.label.spreadsheetImportTitle',
        defaultMessage: 'Imported from SpreadSheet : ',
    },
    childabsent: {
        id: 'iaso.polio.label.childabsent',
        defaultMessage: 'Child absent',
    },
    House_not_visited: {
        id: 'iaso.polio.label.house_not_visited',
        defaultMessage: 'House not visited',
    },
    Other: {
        id: 'iaso.polio.label.other',
        defaultMessage: 'Other',
    },
    Vaccinated_but_not_FM: {
        id: 'iaso.polio.label.vaccinated_but_not_fm',
        defaultMessage: 'Vaccinated but not marked',
    },
    Non_Compliance: {
        id: 'iaso.polio.label.non_compliance',
        defaultMessage: 'Non compliance',
    },
    Child_was_asleep: {
        id: 'iaso.polio.label.child_was_asleep',
        defaultMessage: 'Child asleep',
    },
    Child_is_a_visitor: {
        id: 'iaso.polio.label.child_is_a_visitor',
        defaultMessage: 'Child is a visitor',
    },
    reasonsNoFingerMarked: {
        id: 'iaso.polio.label.reasonsNoFingerMarked',
        defaultMessage: 'Reasons finger not marked',
    },
    childrenNoMark: {
        id: 'iaso.polio.label.childrenNoMark',
        defaultMessage: 'Children not marked',
    },
    caregivers_informed: {
        id: 'iaso.polio.label.caregivers_informed',
        defaultMessage: 'Caregivers informed',
    },
    Others: {
        id: 'iaso.polio.label.others',
        defaultMessage: 'Others',
    },
    TV: {
        id: 'iaso.polio.label.TV',
        defaultMessage: 'TV',
    },
    Radio: {
        id: 'iaso.polio.label.Radio',
        defaultMessage: 'Radio',
    },
    Gong_gong: {
        id: 'iaso.polio.label.Gong_gong',
        defaultMessage: 'Gong gong',
    },
    Mob_VanPA: {
        id: 'iaso.polio.label.Mob_VanPA',
        defaultMessage: 'Mob_VanPA',
    },
    H2H_Mobilizer: {
        id: 'iaso.polio.label.H2H_Mobilizer',
        defaultMessage: 'H2H_Mobilizer',
    },
    IEC_Materials: {
        id: 'iaso.polio.label.IEC_Materials',
        defaultMessage: 'IEC_Materials',
    },
    Volunteers: {
        id: 'iaso.polio.label.Volunteers',
        defaultMessage: 'Volunteers',
    },
    Health_worker: {
        id: 'iaso.polio.label.Health_worker',
        defaultMessage: 'Health worker',
    },
    Opinion_leader: {
        id: 'iaso.polio.label.Opinion_leader',
        defaultMessage: 'Opinion leader',
    },
    Com_Info_centre: {
        id: 'iaso.polio.label.Com_Info_centre',
        defaultMessage: 'Com_Info_centre',
    },
    Religious_leader: {
        id: 'iaso.polio.label.Religious_leader',
        defaultMessage: 'Religious leader',
    },
    MobileMessaging_SocialMedia: {
        id: 'iaso.polio.label.MobileMessaging_SocialMedia',
        defaultMessage: 'Mobile messaging or social media',
    },
    numberCaregiversInformed: {
        id: 'iaso.polio.label.numberCaregiversInformed',
        defaultMessage: 'Number of caregivers informed',
    },
    ratioCaregiversInformed: {
        id: 'iaso.polio.label.ratioCaregiversInformed',
        defaultMessage: 'caregivers informed',
    },
    imGlobal: {
        id: 'iaso.polio.label.imGlobal',
        defaultMessage: 'Global IM',
    },
    imIHH: {
        id: 'iaso.polio.label.imIHH',
        defaultMessage: 'IM in household',
    },
    imOHH: {
        id: 'iaso.polio.label.imOHH',
        defaultMessage: 'IM out of household',
    },
    Tot_child_Absent_HH: {
        id: 'iaso.polio.label.Tot_child_Absent_HH',
        defaultMessage: 'Child absent',
    },
    Tot_child_Asleep_HH: {
        id: 'iaso.polio.label.Tot_child_Asleep_HH',
        defaultMessage: 'Child asleep',
    },
    Tot_child_NC_HH: {
        id: 'iaso.polio.label.Tot_child_NC_HH',
        defaultMessage: 'Refusal',
    },
    Tot_child_NotVisited_HH: {
        id: 'iaso.polio.label.Tot_child_NotVisited_HH',
        defaultMessage: 'Not visited',
    },
    Tot_child_NotRevisited_HH: {
        id: 'iaso.polio.label.Tot_child_NotRevisited_HH',
        defaultMessage: 'Not revisited',
    },
    Tot_child_Others_HH: {
        id: 'iaso.polio.label.Tot_child_Others_HH',
        defaultMessage: 'Other',
    },
    Tot_child_VaccinatedRoutine: {
        id: 'iaso.polio.label.Tot_child_VaccinatedRoutine',
        defaultMessage: 'Child vaccinated in routine',
    },
    noDataFound: {
        id: 'iaso.polio.label.noDataFound',
        defaultMessage: 'No data found',
    },
    collectionStats: {
        id: 'iaso.polio.label.collectionStats',
        defaultMessage: 'Collection stats',
    },
    reportingDistricts: {
        id: 'iaso.polio.label.reportingDistricts',
        defaultMessage: 'Reporting districts',
    },
    total_child_checked: {
        id: 'iaso.polio.label.total_child_checked',
        defaultMessage: 'Children seen',
    },
    total_sites_visited: {
        id: 'iaso.polio.label.total_sites_visited',
        defaultMessage: 'Sites visited',
    },
    ratioUnvaccinated: {
        id: 'iaso.polio.label.ratioUnvaccinated',
        defaultMessage: 'Unvaccinated',
    },
    mainCaregiverInfoSource: {
        id: 'iaso.polio.label.mainCaregiverInfoSource',
        defaultMessage: 'Main source of information',
    },
    totalCaregiversSurveyed: {
        id: 'iaso.polio.label.totalCaregiversSurveyed',
        defaultMessage: 'Caregivers surveyed',
    },
    noScope: {
        id: 'iaso.polio.label.noScope',
        defaultMessage: 'Plese select a scope for the campaign',
    },
    districtsNeedMatching: {
        id: 'iaso.polio.label.districtsNeedMatching',
        defaultMessage: 'Some districts need matching. Please contact an admin',
    },
    noScopeFound: {
        id: 'iaso.polio.label.noScopeFound',
        defaultMessage: 'No scope found',
    },
    childrenNfmAbsent: {
        id: 'iaso.polio.label.childrenNfmAbsent',
        defaultMessage: 'Children absent',
    },
    reasonsForAbsence: {
        id: 'iaso.polio.label.reasonsForAbsence',
        defaultMessage: 'Reasons for absence of non-vaccinated children',
    },
    Market: {
        id: 'iaso.polio.label.market',
        defaultMessage: 'Market',
    },
    Tot_child_Abs_Market: {
        id: 'iaso.polio.label.market',
        defaultMessage: 'Market',
    },
    In_playground: {
        id: 'iaso.polio.label.playground',
        defaultMessage: 'At playground',
    },
    Tot_child_Abs_Play_areas: {
        id: 'iaso.polio.label.playground',
        defaultMessage: 'At playground',
    },
    Farm: {
        id: 'iaso.polio.label.farm',
        defaultMessage: 'Farm',
    },
    Tot_child_Abs_Farm: {
        id: 'iaso.polio.label.farm',
        defaultMessage: 'Farm',
    },
    School: {
        id: 'iaso.polio.label.school',
        defaultMessage: 'School',
    },
    Tot_child_Abs_School: {
        id: 'iaso.polio.label.school',
        defaultMessage: 'School',
    },
    Travelled: {
        id: 'iaso.polio.label.travelled',
        defaultMessage: 'Travelling',
    },
    Tot_child_Abs_Travelling: {
        id: 'iaso.polio.label.travelled',
        defaultMessage: 'Travelling',
    },
    unknown: {
        id: 'iaso.polio.label.unknown',
        defaultMessage: 'Unknown',
    },
    Tot_child_Abs_Social_event: {
        id: 'iaso.polio.label.socialEvent',
        defaultMessage: 'Social event',
    },
    Tot_child_Abs_Parent_Absent: {
        id: 'iaso.polio.label.parentAbsent',
        defaultMessage: 'Parent absent',
    },
    Tot_child_Abs_Other: {
        id: 'iaso.polio.label.other',
        defaultMessage: 'Other',
    },
    showOnlyDeleted: {
        id: 'iaso.polio.showDeletedCampaigns',
        defaultMessage: 'Show deleted campaigns',
    },
    deleted_at: {
        id: 'iaso.forms.deleted_at',
        defaultMessage: 'Deleted',
    },
    restoreCampaign: {
        id: 'iaso.polio.restoreCampaign',
        defaultMessage: 'Restore campaign',
    },
    all: {
        id: 'iaso.polio.label.all',
        defaultMessage: 'All',
    },
    ALL: {
        id: 'iaso.polio.label.all',
        defaultMessage: 'All',
    },
    regular: {
        id: 'iaso.polio.label.regular',
        defaultMessage: 'Regular',
    },
    campaignType: {
        id: 'iaso.polio.label.campaignType',
        defaultMessage: 'Campaign type',
    },
    campaign_types: {
        id: 'iaso.polio.label.campaignTypes',
        defaultMessage: 'Types',
    },
    campaignCategory: {
        id: 'iaso.polio.label.campaignCategory',
        defaultMessage: 'Campaign category',
    },
    lqasImDateTooltip: {
        id: 'iaso.polio.tooltip.label.lqasImDate',
        defaultMessage:
            'No date found in campaign data, using default value based on round date',
    },
    noDateFound: {
        id: 'iaso.polio.placeholder.noDateFound',
        defaultMessage: 'No date found',
    },
    preparednessIntro: {
        id: 'iaso.polio.preparednessIntro',
        defaultMessage:
            'Configure the Google Sheets that will be used to import the preparedness data for the round.',
    },
    preparednessRoundStarted: {
        id: 'iaso.polio.preparednessRoundStarted',
        defaultMessage: "Preparedness can't be edited if round already started",
    },
    badRoundNumbers: {
        id: 'iaso.polio.badRoundNumbers',
        defaultMessage: 'Forms with the wrong round number',
    },
    groupedCampaigns: {
        defaultMessage: 'EPID Blocks',
        id: 'iaso.polio.label.groupedCampaigns',
    },
    countryBlock: {
        defaultMessage: 'Country block',
        id: 'iaso.polio.label.countryBlock',
    },
    updated_at: {
        id: 'iaso.forms.updated_at',
        defaultMessage: 'Updated',
    },
    created_at: {
        id: 'iaso.forms.created_at',
        defaultMessage: 'Created',
    },
    deleteTitle: {
        id: 'iaso.entities.dialog.deleteTitle',
        defaultMessage: 'Are you sure you want to delete this entity?',
    },
    deleteText: {
        id: 'iaso.label.deleteText',
        defaultMessage: 'This operation cannot be undone.',
    },
    save: {
        id: 'iaso.label.save',
        defaultMessage: 'Save',
    },
    close: {
        id: 'iaso.label.close',
        defaultMessage: 'Close',
    },
    editGroupedCampaign: {
        id: 'iaso.polio.label.editGroupedCampaign',
        defaultMessage: 'Edit grouped campaign',
    },
    campaignsToLink: {
        id: 'iaso.polio.label.campaignsToLink',
        defaultMessage: 'Campaigns to link',
    },
    testCampaign: {
        id: 'iaso.polio.label.testCampaign',
        defaultMessage: 'Test campaign/On hold',
    },
    hasSubActivities: {
        id: 'iaso.polio.label.hasSubActivities',
        defaultMessage: 'Round with sub-activities',
    },
    round: {
        id: 'iaso.polio.label.round',
        defaultMessage: 'Round',
    },
    rounds: {
        id: 'iaso.polio.form.label.rounds',
        defaultMessage: 'Rounds',
    },
    roundEmptyStartDate: {
        id: 'iaso.polio.forms.emptyStartDate',
        defaultMessage: 'Round {roundNumber} has no start date',
    },
    roundEmptyEndDate: {
        id: 'iaso.polio.forms.emptyEndDate',
        defaultMessage: 'Round {roundNumber} has no end date',
    },
    deleteRound: {
        id: 'iaso.polio.forms.deleteRound',
        defaultMessage: 'Delete round',
    },
    lastRound: {
        id: 'iaso.polio.label.lastRound',
        defaultMessage: 'Last round',
    },
    fieldRequired: {
        id: 'iaso.polio.form.fieldRequired',
        defaultMessage: 'This field is required',
    },
    invalidDate: {
        id: 'iaso.polio.form.invalidDate',
        defaultMessage: 'Date is invalid',
    },
    startDatefrom: {
        id: 'iaso.label.startDatefrom',
        defaultMessage: 'Start date from',
    },
    endDateUntil: {
        id: 'iaso.label.endDateUntil',
        defaultMessage: 'End date until',
    },
    addCampaign: {
        id: 'iaso.polio.budget.label.addCampaign',
        defaultMessage: 'Add campaign',
    },
    details: {
        defaultMessage: 'Details',
        id: 'iaso.label.details',
    },
    author: {
        defaultMessage: 'Author',
        id: 'iaso.polio.label.author',
    },
    destination: {
        defaultMessage: 'Destination',
        id: 'iaso.polio.label.destination',
    },
    note: {
        defaultMessage: 'note',
        id: 'iaso.polio.label.note',
    },
    notes: {
        defaultMessage: 'comments',
        id: 'iaso.polio.label.notes',
    },
    submission: {
        defaultMessage: 'Submission',
        id: 'iaso.polio.label.submission',
    },
    comments: {
        defaultMessage: 'Comments',
        id: 'iaso.polio.label.comments',
    },
    comment: {
        defaultMessage: 'Comment',
        id: 'iaso.polio.label.comment',
    },
    validation_ongoing: {
        defaultMessage: 'Approval ongoing',
        id: 'iaso.polio.label.approval_ongoing',
    },
    validated: {
        defaultMessage: 'Approved',
        id: 'iaso.polio.label.approved',
    },
    rejected: {
        defaultMessage: 'Rejected',
        id: 'iaso.polio.label.rejected',
    },
    newBudgetStep: {
        defaultMessage: 'New budget step',
        id: 'iaso.polio.label.newBudgetStep',
    },
    resendFiles: {
        defaultMessage: 'Retry sending files',
        id: 'iaso.polio.label.resendFiles',
    },
    addStep: {
        defaultMessage: 'Add step',
        id: 'iaso.polio.label.addStep',
    },
    send: {
        defaultMessage: 'Send',
        id: 'iaso.polio.label.send',
    },
    step: {
        defaultMessage: 'Step',
        id: 'iaso.polio.label.step',
    },
    cc_emails: {
        defaultMessage: 'Cc emails',
        id: 'iaso.polio.label.cc_emails',
    },
    filesUpload: {
        defaultMessage: 'Files',
        id: 'iaso.polio.label.filesUpload',
    },
    viewFiles: {
        defaultMessage: 'View files',
        id: 'iaso.polio.label.viewFiles',
    },
    noFile: {
        defaultMessage: 'No file found',
        id: 'iaso.polio.label.noFile',
    },
    steps: {
        defaultMessage: 'Steps',
        id: 'iaso.polio.label.steps',
    },
    budgetFiles: {
        defaultMessage: '{type} sent by {author} to {recipients} on {date}',
        id: 'iaso.polio.label.budgetFiles',
    },
    noBudgetSubmitted: {
        defaultMessage: 'No budget submitted',
        id: 'iaso.polio.label.noBudgetSubmitted',
    },
    budgetEventCreated: {
        defaultMessage: 'New budget step created',
        id: 'iaso.polio.label.budgetEventCreated',
    },
    budgetUpdated: {
        defaultMessage: 'Budget updated',
        id: 'iaso.polio.label.budgetUpdated',
    },
    tryUpdateStep: {
        defaultMessage: 'Resend budget data?',
        id: 'iaso.polio.title.tryUpdateStep',
    },
    budgetFilesUploaded: {
        defaultMessage: 'Budget files uploaded',
        id: 'iaso.polio.label.budgetFilesUploaded',
    },
    budgetEventFinalized: {
        defaultMessage: 'Budget event finalized',
        id: 'iaso.polio.label.budgetEventFinalized',
    },
    requiredField: {
        id: 'iaso.forms.error.fieldRequired',
        defaultMessage: 'This field is required',
    },
    validation: {
        id: 'iaso.polio.forms.options.approval',
        defaultMessage: 'Approval',
    },
    emailFormat: {
        id: 'iaso.forms.options.emailFormat',
        defaultMessage: 'Please use correctly formatted email addresses',
    },
    urlFormat: {
        id: 'iaso.forms.options.urlFormat',
        defaultMessage: 'Please use correctly formatted URL',
    },
    budgetTypeError: {
        id: 'iaso.forms.options.budgetTypeError',
        defaultMessage:
            'Value should be one of "submission", "comments" or "validation"',
    },
    links: {
        defaultMessage: 'Links',
        id: 'iaso.label.links',
    },
    deleteBudgetEvent: {
        defaultMessage: 'Delete budget event',
        id: 'iaso.polio.label.deleteBudgetEvent',
    },
    showDeleted: {
        id: 'iaso.polio.label.showDeleted',
        defaultMessage: 'Show deleted',
    },
    restore: {
        id: 'iaso.polio.label.restore',
        defaultMessage: 'Restore',
    },
    internal: {
        id: 'iaso.polio.label.internal',
        defaultMessage: 'Internal',
    },
    approve: {
        id: 'iaso.polio.label.approve',
        defaultMessage: 'Approve',
    },
    approveBudgetForCampaign: {
        id: 'iaso.polio.label.approveBudgetForCampaign',
        defaultMessage: 'Approve budget for campaign: {campaign}',
    },
    approveBudget: {
        id: 'iaso.polio.label.approveBudget',
        defaultMessage: 'Approve budget?',
    },
    rejectBudget: {
        id: 'iaso.polio.label.rejectBudget',
        defaultMessage: 'Reject budget?',
    },
    sendComment: {
        id: 'iaso.polio.label.sendComment',
        defaultMessage: 'Send comment',
    },
    rejectBudgetForCampaign: {
        id: 'iaso.polio.label.rejectBudgetForCampaign',
        defaultMessage: 'Reject budget for campaign: {campaign}',
    },
    Community_leader: {
        id: 'iaso.polio.label.Community_leader',
        defaultMessage: 'Community leader',
    },
    Neighbour: {
        id: 'iaso.polio.label.Neighbour',
        defaultMessage: 'Neighbour',
    },
    Teachers_Student: {
        id: 'iaso.polio.label.Teachers_Student',
        defaultMessage: 'Teachers',
    },
    Town_crier: {
        id: 'iaso.polio.label.Town_crier',
        defaultMessage: 'Town crier',
    },
    by: {
        id: 'iaso.polio.label.by',
        defaultMessage: 'by {author}',
    },
    onDate: {
        id: 'iaso.polio.label.onDate',
        defaultMessage: 'on {date}',
    },
    seeFullComment: {
        id: 'iaso.polio.label.seeFullComment',
        defaultMessage: 'See full comment',
    },
    files: {
        id: 'iaso.polio.label.files',
        defaultMessage: 'files',
    },
    see: {
        id: 'iaso.polio.label.see',
        defaultMessage: 'See',
    },
    add: {
        id: 'iaso.polio.label.add',
        defaultMessage: 'Add',
    },
    cannotDisplayMap: {
        id: 'iaso.polio.label.cannotDisplayMap',
        defaultMessage: 'Cannot display map',
    },
    map: {
        id: 'iaso.polio.label.map',
        defaultMessage: 'Map',
    },
    amount: {
        id: 'iaso.polio.label.amount',
        defaultMessage: 'Amount',
    },
    review: {
        id: 'iaso.polio.label.review',
        defaultMessage: 'Review',
    },
    transmission: {
        id: 'iaso.polio.label.transmission',
        defaultMessage: 'Transmission',
    },
    feedback: {
        id: 'iaso.polio.label.feedback',
        defaultMessage: 'Feedback',
    },
    request: {
        id: 'iaso.polio.label.request',
        defaultMessage: 'Request',
    },
    seeProcedure: {
        id: 'iaso.polio.label.seeProcedure',
        defaultMessage: 'See procedure',
    },
    sentToTeam: {
        id: 'iaso.polio.label.sentToTeam',
        defaultMessage: 'Sent to team',
    },
    sentByTeam: {
        id: 'iaso.polio.label.sentByTeam',
        defaultMessage: 'Sent by team',
    },
    exportToPdf: {
        id: 'iaso.polio.label.exportToPdf',
        defaultMessage: 'Export to pdf',
    },
    exportToExcel: {
        id: 'iaso.polio.label.exportToExcel',
        defaultMessage: 'Export to XLSX',
    },
    downloadScopesToCsv: {
        id: 'iaso.polio.label.downloadScopesToCsv',
        defaultMessage: 'Download scopes',
    },
    userWithoutTeam: {
        id: 'iaso.polio.error.label.userWithoutTeam',
        defaultMessage: 'User should be part of a team',
    },
    userNeedsTeam: {
        id: 'iaso.polio.error.label.userNeedsTeam',
        defaultMessage:
            'You need to be part of a team to create or edit budget events',
    },
    // DEPRECATED
    vialsDestroyed: {
        id: 'iaso.polio.label.vialsDestroyed',
        defaultMessage: 'Unusable vials destroyed',
    },
    vials_destroyed: {
        id: 'iaso.polio.label.vialsDestroyed',
        defaultMessage: 'Unusable vials destroyed',
    },
    destructions: {
        id: 'iaso.polio.label.destructions',
        defaultMessage: 'Destructions',
    },
    destructionReceptionDate: {
        id: 'iaso.polio.label.destructionReceptionDate',
        defaultMessage: 'Reception of the destruction report',
    },
    destructionReportDate: {
        id: 'iaso.polio.label.destructionReportDate',
        defaultMessage: 'Date of the destruction report',
    },
    dateSignedVrf: {
        id: 'iaso.polio.label.dateSignedVrf',
        defaultMessage: 'Date signed VRF received',
    },
    date_signed_vrf_received: {
        id: 'iaso.polio.label.dateSignedVrf',
        defaultMessage: 'Date signed VRF received',
    },
    reportingDelays: {
        id: 'iaso.polio.label.reportingDelays',
        defaultMessage: 'Reporting delays',
    },
    reporting_delays_hc_to_district: {
        id: 'iaso.polio.label.healthCentreToDistrict',
        defaultMessage: 'Health centers to district',
    },
    reporting_delays_district_to_region: {
        id: 'iaso.polio.label.districtToRegionalLevel',
        defaultMessage: 'District to regional level',
    },
    reporting_delays_region_to_national: {
        id: 'iaso.polio.label.regionalToNationalLevel',
        defaultMessage: 'Regional to national level',
    },
    healthCentreToDistrict: {
        id: 'iaso.polio.label.healthCentreToDistrict',
        defaultMessage: 'Health centers to district',
    },
    districtToRegionalLevel: {
        id: 'iaso.polio.label.districtToRegionalLevel',
        defaultMessage: 'District to regional level',
    },
    regionalToNationalLevel: {
        id: 'iaso.polio.label.regionalToNationalLevel',
        defaultMessage: 'Regional to national level',
    },
    receptionPreAlert: {
        id: 'iaso.polio.label.receptionPreAlert',
        defaultMessage: 'Reception of the pre-alert',
    },
    receptionVaccineArrivalReport: {
        id: 'iaso.polio.label.receptionVaccineArrivalReport',
        defaultMessage: 'Reception of Arrival Report',
    },

    vialsShipped: {
        id: 'iaso.polio.label.vialsShipped',
        defaultMessage: 'Vials shipped',
    },
    vials_received: {
        id: 'iaso.polio.label.vialsShipped',
        defaultMessage: 'Vials shipped',
    },
    po_numbers: {
        id: 'iaso.polio.label.poNumbers',
        defaultMessage: 'PO numbers',
    },
    poNumbers: {
        id: 'iaso.polio.label.poNumbers',
        defaultMessage: 'PO numbers',
    },
    formAReception: {
        id: 'iaso.polio.label.formAReception',
        defaultMessage: 'Reception of national Form A',
    },
    forma_reception: {
        id: 'iaso.polio.label.formAReception',
        defaultMessage: 'Reception of national Form A',
    },
    formADate: {
        id: 'iaso.polio.label.formADate',
        defaultMessage: 'Form A date',
    },
    forma_date: {
        id: 'iaso.polio.label.formADate',
        defaultMessage: 'Form A date',
    },
    formAComment: {
        id: 'iaso.polio.label.formAComment',
        defaultMessage: 'Comment on form A',
    },
    forma_comment: {
        id: 'iaso.polio.label.formAComment',
        defaultMessage: 'Comment on form A',
    },
    formAUsableVials: {
        id: 'iaso.polio.label.formAUsableVials',
        defaultMessage: 'Usable vials',
    },
    forma_usable_vials: {
        id: 'iaso.polio.label.formAUsableVials',
        defaultMessage: 'Usable vials',
    },
    formAUnusableVials: {
        id: 'iaso.polio.label.formAUnusableVials',
        defaultMessage: 'Unusable vials',
    },
    forma_unusable_vials: {
        id: 'iaso.polio.label.formAUnusableVials',
        defaultMessage: 'Unusable vials',
    },
    formAMissingVials: {
        id: 'iaso.polio.label.formAMissingVials',
        defaultMessage: 'Number of missing vials from the national form',
    },
    forma_missing_vials: {
        id: 'iaso.polio.label.formAMissingVials',
        defaultMessage: 'Number of missing vials from the national form',
    },
    // END DEPRECATED
    days: {
        id: 'iaso.polio.label.days',
        defaultMessage: 'Days',
    },
    vaccineManagement: {
        id: 'iaso.polio.label.vaccineManagement',
        defaultMessage: 'Vaccine management',
    },
    shipment: {
        id: 'iaso.polio.label.shipment',
        defaultMessage: 'Shipment',
    },
    shipments: {
        id: 'iaso.polio.label.shipments',
        defaultMessage: 'Shipments',
    },
    formA: {
        id: 'iaso.polio.label.formA',
        defaultMessage: 'Form A',
    },
    destruction: {
        id: 'iaso.polio.label.destruction',
        defaultMessage: 'Destruction',
    },
    date_destruction: {
        id: 'iaso.polio.label.destructionDate',
        defaultMessage: 'Destruction date',
    },
    addVaccine: {
        id: 'iaso.polio.label.addVaccine',
        defaultMessage: 'Add vaccine',
    },
    removeLastVaccine: {
        id: 'iaso.polio.label.removeLastVaccine',
        defaultMessage: 'Remove last vaccine',
    },
    addShipment: {
        id: 'iaso.polio.label.addShipment',
        defaultMessage: 'Add shipment',
    },
    removeLastShipment: {
        id: 'iaso.polio.label.removeLastShipment',
        defaultMessage: 'Remove last shipment',
    },
    addDestruction: {
        id: 'iaso.polio.label.addDestruction',
        defaultMessage: 'Add destruction',
    },
    removeLastDestruction: {
        id: 'iaso.polio.label.removeLastDestruction',
        defaultMessage: 'Remove last destruction',
    },
    addLink: {
        id: 'iaso.polio.label.addLink',
        defaultMessage: 'Add link',
    },
    removeLastLink: {
        id: 'iaso.polio.label.removeLastLink',
        defaultMessage: 'Remove last link',
    },
    destructionDateAndVialsDestroyed: {
        id: 'iaso.polio.label.destructionDateAndVialsDestroyed',
        defaultMessage:
            'Destruction date and Vials destroyed need to be filled together',
    },
    formaFieldsTogether: {
        id: 'iaso.polio.label.formaFieldsTogether',
        defaultMessage: 'All Form A fields need to be filled together',
    },
    shipmentFieldsTogether: {
        id: 'iaso.polio.label.shipmentFieldsTogether',
        defaultMessage: 'All shipment fields need to be filled together',
    },
    destructionFieldsTogether: {
        id: 'iaso.polio.label.destructionFieldsTogether',
        defaultMessage: 'All destruction fields need to be filled together',
    },
    scopeUnlockConditions: {
        id: 'iaso.polio.label.scopeUnlockConditions',
        defaultMessage:
            'Select initial region and encode dates for at least one round to unlock Scope tab',
    },
    campaignHistory: {
        id: 'iaso.polio.campaign.campaignHistory',
        defaultMessage: 'Campaign History',
    },
    campaingDropdownLabel: {
        id: 'iaso.polio.label.campaignDropdownLabel',
        defaultMessage: 'Modification date',
    },
    error: {
        id: 'iaso.polio.campaign.campaignHistory.error',
        defaultMessage: 'Can not find an history with this campaign or log id',
    },
    key: {
        id: 'iaso.polio.campaign.key',
        defaultMessage: 'Key',
    },
    label: {
        id: 'iaso.polio.label.label',
        defaultMessage: 'Label',
    },
    value: {
        id: 'iaso.polio.campaign.value',
        defaultMessage: 'Value',
    },
    typeNotSupported: {
        id: 'iaso.polio.campaign.typeNotSupported',
        defaultMessage: 'Type not supported yet: {type}',
    },
    last_modified_by: {
        id: 'iaso.instance.last_modified_by',
        defaultMessage: 'Modified by',
    },
    seeLogDetail: {
        id: 'iaso.polio.campaign.seeLogDetail',
        defaultMessage: 'See more details',
    },
    form: {
        id: 'iaso.polio.campaign.form',
        defaultMessage: 'Form',
    },
    initial_org_unit: {
        id: 'iaso.polio.campaign.initial_org_unit',
        defaultMessage: 'Org Unit',
    },
    gpei_email: {
        id: 'iaso.polio.label.gpei_email',
        defaultMessage: 'Email GPEI',
    },
    pv_notified_at: {
        id: 'iaso.polio.label.pv_notified_at',
        defaultMessage: 'PV Notification',
    },
    three_level_call_at: {
        id: 'iaso.polio.form.label.threelevelCall',
        defaultMessage: '3 level call',
    },
    detection_status: {
        id: 'iaso.polio.label.detection_status',
        defaultMessage: 'Detection status',
    },
    creation_email_send_at: {
        id: 'iaso.polio.label.creation_email_send_at',
        defaultMessage: 'Email creation date',
    },
    risk_assessment_responsible: {
        id: 'iaso.polio.label.risk_assessment_responsible',
        defaultMessage: 'Risk assessment responsible',
    },
    id: {
        id: 'iaso.polio.label.campaign.id',
        defaultMessage: 'Id',
    },
    group: {
        id: 'iaso.polio.label.group',
        defaultMessage: 'Group',
    },
    number: {
        id: 'iaso.polio.label.round.number',
        defaultMessage: 'Round number',
    },
    domain: {
        id: 'iaso.polio.label.domain',
        defaultMessage: 'Domain',
    },
    attachments: {
        id: 'iaso.polio.label.attachments',
        defaultMessage: 'Attachments',
    },
    clickToHide: {
        id: 'iaso.polio.label.clickToHide',
        defaultMessage: 'Click to hide',
    },
    clickToShow: {
        id: 'iaso.polio.label.clickToShow',
        defaultMessage: 'Click to show',
    },
    showHidden: {
        id: 'iaso.polio.label.showHidden',
        defaultMessage: 'Show hidden',
    },
    url: {
        id: 'iaso.polio.label.url',
        defaultMessage: 'Url',
    },
    displayedName: {
        id: 'iaso.polio.label.displayedName',
        defaultMessage: 'Displayed name',
    },
    linksOrFilesRequired: {
        id: 'iaso.polio.label.linksOrFilesRequired',
        defaultMessage: 'You need to attach at least a link or a file',
    },
    lastStep: {
        id: 'iaso.polio.label.lastStep',
        defaultMessage: 'Last step',
    },
    nextSteps: {
        id: 'iaso.polio.label.nextSteps',
        defaultMessage: 'Possible next steps',
    },
    searchInScopeOrAllDistricts: {
        id: 'iaso.polio.label.searchInScopeOrAllDistricts',
        defaultMessage: 'Search districts in scope',
    },
    emailWillBeSentTo: {
        id: 'iaso.polio.label.emailWillBeSentTo',
        defaultMessage: 'The following teams will be notified by email:',
    },
    teams: {
        id: 'iaso.polio.config.teams',
        defaultMessage: 'Team(s) for the Budget workflow',
    },
    rrtOprttApproval: {
        id: 'iaso.polio.form.label.rrtOprttApproval',
        defaultMessage: 'RRT/OPRTT Approval',
    },
    risk_assessment_rrt_oprtt_approval_at: {
        id: 'iaso.polio.form.label.risk_assessment_rrt_oprtt_approval_at',
        defaultMessage: 'RRT/ORPG-Approval',
    },
    loading: {
        id: 'iaso.label.loading',
        defaultMessage: 'Loading',
    },
    noOptions: {
        id: 'iaso.label.noOptions',
        defaultMessage: 'No result found',
    },
    selectRoundsToDisplay: {
        id: 'iaso.polio.form.label.selectRoundsToDisplay',
        defaultMessage: 'Select rounds to display',
    },
    latest: {
        id: 'iaso.polio.form.label.latest',
        defaultMessage: 'Latest',
    },
    re_submitted_to_orpg: {
        id: 'iaso.polio.form.label.re_submitted_to_orpg_wider',
        defaultMessage: 'Resubmitted to ORPG wider group',
    },
    override: {
        id: 'iaso.polio.form.label.override',
        defaultMessage: 'Override',
    },
    newBudgetState: {
        id: 'iaso.polio.form.label.newBudgetState',
        defaultMessage: 'New budget state',
    },
    budget_current_state_label: {
        id: 'iaso.polio.form.label.newBudgetState',
        defaultMessage: 'New budget state',
    },
    stepCancelled: {
        id: 'iaso.polio.form.label.stepCancelled',
        defaultMessage: 'Admin override cancelled this step',
    },
    stepSkipped: {
        id: 'iaso.polio.form.label.stepSkipped',
        defaultMessage: 'Admin override skipped this step',
    },
    TO_SUBMIT: {
        id: 'iaso.polio.form.label.TO_SUBMIT',
        defaultMessage: 'To submit',
    },
    SUBMITTED: {
        id: 'iaso.polio.form.label.SUBMITTED',
        defaultMessage: 'Submitted',
    },
    REVIEWED: {
        id: 'iaso.polio.form.label.REVIEWED',
        defaultMessage: 'Reviewed by RRT',
    },
    APPROVED: {
        id: 'iaso.polio.form.label.APPROVED',
        defaultMessage: 'Approved',
    },
    date: {
        id: 'iaso.polio.form.label.date',
        defaultMessage: 'Date',
    },
    editionDisabled: {
        id: 'iaso.polio.form.label.editionDisabled',
        defaultMessage: 'Edition disabled',
    },
    repeatBudgetStep: {
        id: 'iaso.polio.form.label.repeatBudgetStep',
        defaultMessage: 'Re-send step for corrections or as reminder',
    },
    importExcelLinefile: {
        id: 'iaso.polio.import_file.label',
        defaultMessage: 'Excel Line File',
    },
    futureDateError: {
        id: 'iaso.polio.validation.futureDateError',
        defaultMessage: 'This date should not be in the future',
    },
    onsetAfterNotificationError: {
        id: 'iaso.polio.validation.onsetAfterNotificationError',
        defaultMessage: 'Date of onset should be before virus notification',
    },
    onsetAfterOutbreakDeclarationError: {
        id: 'iaso.polio.validation.onsetAfterOutbreakDeclarationError',
        defaultMessage: 'Date of onset should be before outbreak declaration',
    },
    virusNotificationAfterOutbreakDeclarationError: {
        id: 'iaso.polio.validation.virusNotificationAfterOutbreakDeclarationError',
        defaultMessage:
            'Virus notification should be before outbreak declaration',
    },
    reasonForDateChange: {
        id: 'iaso.polio.label.reasonForDateChange',
        defaultMessage: 'Reason for date change',
    },
    editRoundDates: {
        id: 'iaso.polio.label.editRoundDates',
        defaultMessage: 'Edit round dates',
    },
    ENCODING_ERROR: {
        id: 'iaso.polio.label.ENCODING_ERROR',
        defaultMessage: 'Encoding error',
    },
    INITIAL_DATA: {
        id: 'iaso.polio.label.INITIAL_DATA',
        defaultMessage: 'Initial data',
    },
    VACCINES_NOT_ARRIVED_IN_COUNTRY: {
        id: 'iaso.polio.label.VACCINES_NOT_ARRIVED_IN_COUNTRY',
        defaultMessage: 'Vaccines not arrived in country',
    },
    VACCINES_NOT_DELIVERED_OPS_LEVEL: {
        id: 'iaso.polio.label.VACCINES_NOT_DELIVERED_OPS_LEVEL',
        defaultMessage: 'Vaccines not delivered at operational level',
    },
    FUNDS_NOT_ARRIVED_IN_COUNTRY: {
        id: 'iaso.polio.label.FUNDS_NOT_ARRIVED_IN_COUNTRY',
        defaultMessage: 'Funds not arrived in country',
    },
    FUNDS_NOT_RECEIVED_OPS_LEVEL: {
        id: 'iaso.polio.label.FUNDS_NOT_RECEIVED_OPS_LEVEL',
        defaultMessage: 'Funds not received at operational level',
    },
    PREPAREDNESS_LEVEL_NOT_REACHED: {
        id: 'iaso.polio.label.PREPAREDNESS_LEVEL_NOT_REACHED',
        defaultMessage: 'Preparedness level no reached',
    },
    CAMPAIGN_SYNCHRONIZATION: {
        id: 'iaso.polio.label.CAMPAIGN_SYNCHRONIZATION',
        defaultMessage: 'Campaigns synchronization',
    },
    MOH_DECISION: {
        id: 'iaso.polio.label.MOH_DECISION',
        defaultMessage: 'Decision from MOH',
    },
    OTHER_ACTIVITIES: {
        id: 'iaso.polio.label.OTHER_ACTIVITIES',
        defaultMessage: 'Integrate with other vaccination activities',
    },
    PUBLIC_HOLIDAY: {
        id: 'iaso.polio.label.PUBLIC_HOLIDAY',
        defaultMessage: 'Delayed to observe public holiday',
    },
    SECURITY_CONTEXT: {
        id: 'iaso.polio.label.SECURITY_CONTEXT',
        defaultMessage: 'Security context',
    },
    CAMPAIGN_MOVED_FORWARD_BY_MOH: {
        id: 'iaso.polio.label.CAMPAIGN_MOVED_FORWARD_BY_MOH',
        defaultMessage: 'Campaign moved forward by MOH',
    },
    VRF_NOT_SIGNED: {
        id: 'iaso.polio.label.VRF_NOT_SIGNED',
        defaultMessage: 'VRF not signed',
    },
    FOUR_WEEKS_GAP_BETWEEN_ROUNDS: {
        id: 'iaso.polio.label.FOUR_WEEKS_GAP_BETWEEN_ROUNDS',
        defaultMessage: 'Four weeks gap between rounds to be respected',
    },
    OTHER_VACCINATION_CAMPAIGNS: {
        id: 'iaso.polio.label.OTHER_VACCINATION_CAMPAIGNS',
        defaultMessage: 'Other vaccination campaigns',
    },
    PENDING_LIQUIDATION_OF_PREVIOUS_SIA_FUNDING: {
        id: 'iaso.polio.label.PENDING_LIQUIDATION_OF_PREVIOUS_SIA_FUNDING',
        defaultMessage: 'Pending liquidation of previous SIA funding',
    },
    previousEndDate: {
        id: 'iaso.polio.label.previousEndDate',
        defaultMessage: 'Previous end date',
    },
    previousStartDate: {
        id: 'iaso.polio.label.previousStartDate',
        defaultMessage: 'Previous start date',
    },
    dateOfChange: {
        id: 'iaso.polio.label.dateOfChange',
        defaultMessage: 'Date of change',
    },
    modifiedBy: {
        id: 'iaso.polio.label.modifiedBy',
        defaultMessage: 'Modified by',
    },
    historyForRound: {
        id: 'iaso.polio.label.historyForRound',
        defaultMessage: 'History for round {roundNumber}',
    },
    seeHistory: {
        id: 'iaso.polio.label.seeHistory',
        defaultMessage: 'See history',
    },
    mobilePayment: {
        id: 'iaso.polio.campaign.mobilePayment',
        defaultMessage: 'Mobile Payment',
    },
    lqasMap: {
        id: 'iaso.polio.campaign.lqasMap',
        defaultMessage: 'LQAS map',
    },
    byCountry: {
        id: 'iaso.polio.campaign.byCountry',
        defaultMessage: 'By country',
    },
    penultimate: {
        id: 'iaso.polio.lqasim.penultimate',
        defaultMessage: 'Penultimate',
    },
    legend: {
        id: 'iaso.polio.label.legend',
        defaultMessage: 'Legend',
    },
    '3months': {
        id: 'iaso.polio.label.3months',
        defaultMessage: '3 months',
    },
    '6months': {
        id: 'iaso.polio.label.6months',
        defaultMessage: '6 months',
    },
    '9months': {
        id: 'iaso.polio.label.9months',
        defaultMessage: '9 months',
    },
    '12months': {
        id: 'iaso.polio.label.12months',
        defaultMessage: '12 months',
    },
    latestCampaignForPeriod: {
        id: 'iaso.polio.label.latestCampaignForPeriod',
        defaultMessage: 'Latest campaign for',
    },
    chooseDates: {
        id: 'iaso.polio.label.chooseDates',
        defaultMessage: 'Choose dates',
    },
    refreshLqasData: {
        id: 'iaso.polio.label.refreshLqasData',
        defaultMessage: 'Refresh LQAS data',
    },
    refreshIMData: {
        id: 'iaso.polio.label.refreshIMData',
        defaultMessage: 'Refresh IM data',
    },
    districtsInScope: {
        id: 'iaso.polio.label.districtsInScope',
        defaultMessage: 'Districts in scope',
    },
    vaccinemodule: {
        id: 'iaso.polio.title.vaccinemodule',
        defaultMessage: 'Vaccine module',
    },
    nopv2Auth: {
        id: 'iaso.polio.title.nopv2Auth',
        defaultMessage: 'NOPV2 authorisations',
    },
    editAuth: {
        id: 'iaso.polio.title.editAuth',
        defaultMessage: 'Edit authorisation',
    },
    signature: {
        id: 'iaso.polio.label.signature',
        defaultMessage: 'Signature',
    },
    expired: {
        id: 'iaso.polio.label.expired',
        defaultMessage: 'Expired',
    },
    quantity: {
        id: 'iaso.polio.label.quantity',
        defaultMessage: 'Quantity',
    },
    currentAuthorisedQuantity: {
        id: 'iaso.polio.label.currentAuthorisedQuantity',
        defaultMessage: 'Current authorised quantity',
    },
    expirationDate: {
        id: 'iaso.polio.label.expirationDate',
        defaultMessage: 'Expiration date',
    },
    currentExpirationDate: {
        id: 'iaso.polio.label.currentExpirationDate',
        defaultMessage: 'Current expiration date',
    },
    nextExpirationDate: {
        id: 'iaso.polio.label.nextExpirationDate',
        defaultMessage: 'Next expiration date',
    },
    latestCampaignFrom: {
        id: 'iaso.polio.label.latestCampaignFrom',
        defaultMessage: 'Latest campaign from',
    },
    latestCampaignUntil: {
        id: 'iaso.polio.label.latestCampaignUntil',
        defaultMessage: 'Latest campaign until',
    },
    dateForExpired: {
        id: 'iaso.polio.error.dateForExpired',
        defaultMessage: 'Expired authorisations can only have past dates',
    },
    startDateAfterExpiration: {
        id: 'iaso.polio.error.startDateAfterExpiration',
        defaultMessage: 'Start date must be anterior to expiration date',
    },
    mostRecentAuthStatus: {
        id: 'iaso.polio.table.label.mostRecentAuthStatus',
        defaultMessage: 'Most recent authorisation status',
    },
    vaccineAuthStartDate: {
        id: 'iaso.polio.table.label.vaccineAuthStartDate',
        defaultMessage: 'Start Date',
    },
    afroMapfilterInfo: {
        id: 'iaso.polio.label.afroMapfilterInfo',
        defaultMessage:
            'The latest campaign is the campaign with the round that started the most recently within the chosen time frame',
    },
    vaccineSupplyChain: {
        id: 'iaso.polio.menu.vaccineSupplyChain',
        defaultMessage: 'Supply chain',
    },
    vaccineStockManagement: {
        id: 'iaso.polio.menu.vaccineStockManagement',
        defaultMessage: 'Stock management',
    },
    latestManualRefresh: {
        id: 'iaso.polio.label.latestManualRefresh',
        defaultMessage: 'Latest manual refresh',
    },
    SUCCESS: {
        id: 'iaso.task.label.SUCCESS',
        defaultMessage: 'Success',
    },
    ERRORED: {
        id: 'iaso.task.label.ERRORED',
        defaultMessage: 'Errored',
    },
    RUNNING: {
        id: 'iaso.task.label.RUNNING',
        defaultMessage: 'Running',
    },
    QUEUED: {
        id: 'iaso.task.label.QUEUED',
        defaultMessage: 'Queued',
    },
    SKIPPED: {
        id: 'iaso.task.label.SKIPPED',
        defaultMessage: 'Skipped',
    },
    KILLED: {
        id: 'iaso.task.label.KILLED',
        defaultMessage: 'Killed',
    },
    EXPORTED: {
        id: 'iaso.task.label.EXPORTED',
        defaultMessage: 'Exported',
    },
    gotoLqasForCountry: {
        id: 'iaso.task.label.gotoLqasForCountry',
        defaultMessage: 'See LQAS page',
    },
    list: {
        defaultMessage: 'List',
        id: 'iaso.label.list',
    },
    reasonsForDelay: {
        id: 'iaso.polio.label.reasonsForDelay',
        defaultMessage: 'Reasons for delay',
    },
    name_fr: {
        id: 'iaso.polio.label.name_fr',
        defaultMessage: 'French text',
    },
    name_en: {
        id: 'iaso.polio.label.name_en',
        defaultMessage: 'English text',
    },
    keyName: {
        id: 'iaso.polio.label.keyName',
        defaultMessage: 'Key',
    },
    createReasonForDelay: {
        id: 'iaso.polio.label.createReasonForDelay',
        defaultMessage: 'Create reason for delay',
    },
    editReasonForDelay: {
        id: 'iaso.polio.label.editReasonForDelay',
        defaultMessage: 'Edit reason for delay',
    },
    wrongUserAccount: {
        id: 'iaso.polio.forms.error.wrongUserAccount',
        defaultMessage: 'Wrong user account',
    },
    incorrectFormat: {
        id: 'iaso.polio.forms.error.incorrectFormat',
        defaultMessage: 'Incorrect format',
    },
    keyNameFormat: {
        id: 'iaso.polio.forms.error.keyNameFormat',
        defaultMessage:
            'Unique identifier. Use all caps letters separated by an underscore. No numbers or special characters',
    },
    result: {
        id: 'iaso.polio.label.result',
        defaultMessage: 'Result',
    },
    noRoundFound: {
        id: 'iaso.polio.label.noRoundFound',
        defaultMessage: 'No round found',
    },
    dateRangeTitle: {
        id: 'iaso.polio.label.dateRangeTitle',
        defaultMessage: 'Enter date range',
    },
    notifications: {
        id: 'iaso.polio.label.notifications',
        defaultMessage: 'Virus notification',
    },
    defaultMutationApiSuccess: {
        id: 'iaso.snackBar.successful',
        defaultMessage: 'Saved successfully',
    },
    evaluation: {
        id: 'iaso.polio.label.evaluation',
        defaultMessage: 'Evaluation',
    },
    period: {
        defaultMessage: 'Period',
        id: 'iaso.instance.period',
    },
    semester: {
        defaultMessage: 'Semester',
        id: 'iaso.polio.periods.semester',
    },
    quarter: {
        defaultMessage: 'Quarter',
        id: 'iaso.polio.periods.quarter',
    },
    year: {
        defaultMessage: 'Year',
        id: 'iaso.polio.periods.year',
    },
    goToCampaign: {
        defaultMessage: 'Go to campaign',
        id: 'iaso.polio.lqas.goToCampaign',
    },
    subActivities: {
        defaultMessage: 'Sub-activities',
        id: 'iaso.polio.subActivities',
    },
    // TODO delete this translation
    subActivitiesUnlockConditions: {
        defaultMessage:
            'Select initial region and encode dates for at least one round to unlock sub-activities tab',
        id: 'iaso.polio.subActivitiesUnlockConditions',
    },
    subActivitiesLockedScopeChange: {
        defaultMessage:
            'Sub-activities are locked because you switched the scope level. Please save this campaign first and edit it again to access sub-activities',
        id: 'iaso.polio.subActivitiesLockedScopeChange',
    },
    campaignSaveError: {
        defaultMessage: 'Campaign not saved',
        id: 'iaso.polio.campaignSaveError',
    },
    campaignSaved: {
        defaultMessage: 'Campaign saved',
        id: 'iaso.polio.campaignSaved',
    },
    subActivitySaved: {
        defaultMessage: 'Sub-activity saved',
        id: 'iaso.polio.subActivitySaved',
    },
    subActivitySaveError: {
        defaultMessage: 'Sub-activity not saved',
        id: 'iaso.polio.subActivitySaveError',
    },
    ageMax: {
        defaultMessage: 'Age max',
        id: 'iaso.polio.label.ageMax',
    },
    ageMin: {
        defaultMessage: 'Age min',
        id: 'iaso.polio.label.ageMin',
    },
    ageUnit: {
        defaultMessage: 'Enter age in',
        id: 'iaso.polio.label.ageUnit',
    },
    YEARS: {
        defaultMessage: 'Years',
        id: 'iaso.polio.label.YEARS',
    },
    MONTHS: {
        defaultMessage: 'Months',
        id: 'iaso.polio.label.MONTHS',
    },
    ageMinGreaterOrEqualToAgeMin: {
        defaultMessage: 'Age min should be smaller than age max',
        id: 'iaso.polio.label.ageMinGreaterOrEqualToAgeMin',
    },
    ageMaxSmallerOrEqualToAgeMin: {
        defaultMessage: 'Age max should be greater than age min',
        id: 'iaso.polio.label.ageMaxSmallerOrEqualToAgeMin',
    },
    pleaseSelectAgeType: {
        defaultMessage: 'Please select an age unit',
        id: 'iaso.polio.label.pleaseSelectAgeType',
    },
    other: {
        defaultMessage: 'Other',
        id: 'iaso.label.other',
    },
    chronogram: {
        id: 'iaso.polio.label.chronogram',
        defaultMessage: 'Chronogram',
    },
    notShowTestCampaigns: {
        id: 'iaso.polio.notShowTestCampaigns',
        defaultMessage: 'Do not show test campaigns',
    },
    fileType: {
        id: 'iaso.polio.label.fileType',
        defaultMessage: 'File type',
    },
    campaignStatus: {
        id: 'iaso.polio.label.campaignStatus',
        defaultMessage: 'Campaign status',
    },
    vaccineRepository: {
        id: 'iaso.polio.repository.title',
        defaultMessage: 'Vaccine Management Repository',
    },
    scopesWillBeDeleted: {
        id: 'iaso.polio.campaign.label.scopesWillBeDeleted',
        defaultMessage: 'The previous scopes will be deleted (sub-activity ones included)',
    },
    scopeWarningTitle: {
        id: 'iaso.polio.campaign.label.scopeWarningTitle',
        defaultMessage: 'Scope type has been changed',
    },
    proceed: {
        id: 'blsq.label.proceed',
        defaultMessage: 'proceed',
    },
    doYouWantToClose: {
        id: 'blsq.dialog.doYouWantToClose',
        defaultMessage: 'Do you want to close?',
    },
    unsavedDataWillBeLost: {
        id: 'blsq.dialog.unsavedDataWillBeLost',
        defaultMessage: 'Unsaved data will be lost',
    },
    testRound: {
        id: 'iaso.polio.label.testRound',
        defaultMessage: 'Test round / On hold',
    },
    disclaimer: {
        id: 'iaso.polio.disclaimer',
        defaultMessage:
            'This data is confidential. Please do not share externally without RRT team approval.',
    },
});

export default MESSAGES;
