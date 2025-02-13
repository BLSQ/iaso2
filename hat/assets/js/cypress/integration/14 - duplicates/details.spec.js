/// <reference types="cypress" />

import { find } from 'lodash';
import instancesAInfos from '../../fixtures/duplicates/instances-a.json';
import instancesBInfos from '../../fixtures/duplicates/instances-b.json';
import duplicatesInfos from '../../fixtures/duplicates/list-details.json';
import superUser from '../../fixtures/profiles/me/superuser.json';

let interceptFlag = false;
const siteBaseUrl = Cypress.env('siteBaseUrl');
const baseUrl = `${siteBaseUrl}/dashboard/entities/duplicates/details/accountId/1/entities/883,163`;

const mockPage = () => {
    cy.login();
    cy.intercept('GET', '/sockjs-node/**');
    cy.intercept('GET', '/api/profiles/me/**', {
        fixture: 'profiles/me/superuser.json',
    }).as('getProfile');
    cy.intercept('GET', '/api/entityduplicates/detail/?entities=883%2C163', {
        fixture: 'duplicates/details.json',
    }).as('getDetails');
    cy.intercept('GET', '/api/entityduplicates/?entities=883%2C163', {
        fixture: 'duplicates/list-details.json',
    }).as('getDetailsDuplicate');
    cy.intercept(
        'GET',
        '/api/instances/?order=source_created_at&with_descriptor=true&entityId=163',
        {
            fixture: 'duplicates/instances-a.json',
        },
    ).as('getDetailsInstanceA');
    cy.intercept(
        'GET',
        '/api/instances/?order=source_created_at&with_descriptor=true&entityId=883',
        {
            fixture: 'duplicates/instances-b.json',
        },
    ).as('getDetailsInstanceB');
};

const testCellStatus = (rowIndex, cellIndex, status) => {
    cy.get('@duplicateTableRows')
        .eq(rowIndex)
        .find('td')
        .eq(cellIndex)
        .invoke('attr', 'data-test')
        .should('equal', status);
};
const testCellIsEmpty = (rowIndex, cellIndex) => {
    cy.get('@duplicateTableRows')
        .eq(rowIndex)
        .find('td')
        .eq(cellIndex)
        .find('div')
        .should('be.empty');
};
const testCellContains = (rowIndex, cellIndex, stringToContain) => {
    cy.get('@duplicateTableRows')
        .eq(rowIndex)
        .find('td')
        .eq(cellIndex)
        .find('div')
        .should('contain', stringToContain);
};
describe('Duplicate details', () => {
    it('page should not be accessible if user does not have permission', () => {
        const fakeUser = {
            ...superUser,
            permissions: [],
            is_superuser: false,
        };
        mockPage();
        cy.intercept('GET', '/api/profiles/me/**', fakeUser);
        cy.visit(baseUrl);
        const errorCode = cy.get('#error-code');
        errorCode.should('contain', '403');
    });

    it('should show correct infos', () => {
        mockPage();
        cy.visit(baseUrl);

        cy.wait([
            '@getDetails',
            '@getDetailsDuplicate',
            '@getDetailsInstanceA',
            '@getDetailsInstanceB',
        ]).then(() => {
            cy.url().should('eq', baseUrl);

            // INFOS
            cy.get('[data-test="duplicate-infos"]').as('infos');
            cy.get('@infos')
                .find('h5')
                .should('contain', duplicatesInfos.results[0].form.name);
            cy.get('@infos').find('table').as('infoTable');
            cy.get('@infoTable')
                .find('tbody')
                .find('tr')
                .as('tableRows')
                .should('have.length', 5);
            cy.get('@tableRows').eq(0).find('td').should('have.length', 2);
            cy.get('@tableRows')
                .eq(0)
                .find('td')
                .eq(1)
                .find('[data-test="star-value"]')
                .should('have.attr', 'style', 'width: 40%;');
            cy.get('@tableRows')
                .eq(1)
                .find('td')
                .eq(1)
                .should('contain', '883,163');
            cy.get('@tableRows').eq(2).find('td').eq(1).should('contain', '1');
            cy.get('@tableRows')
                .eq(3)
                .find('td')
                .eq(1)
                .should('contain', 'levenshtein');
            cy.get('@tableRows').eq(4).find('td').eq(1).should('contain', '3');

            // BUTTONS
            cy.get('[data-test="ignore-button"]')
                .invoke('attr', 'disabled')
                .should('equal', undefined);
            cy.get('[data-test="merge-button"]')
                .invoke('attr', 'disabled')
                .should('equal', 'disabled');

            cy.get('[data-test="duplicate-table"]')
                .find('table')
                .as('duplicateTable');

            // TABLE
            cy.get('@duplicateTable')
                .find('tbody')
                .find('tr')
                .as('duplicateTableRows')
                .should('have.length', 4);

            testCellStatus(0, 1, 'diff');
            testCellStatus(0, 2, 'diff');
            testCellIsEmpty(0, 3);

            testCellStatus(1, 1, 'identical');
            testCellStatus(1, 2, 'identical');
            testCellContains(1, 3, 'Côté');

            testCellStatus(2, 1, 'identical');
            testCellStatus(2, 2, 'identical');
            testCellIsEmpty(2, 3);

            testCellStatus(3, 1, 'diff');
            testCellStatus(3, 2, 'diff');
            testCellIsEmpty(3, 3);

            // SUBMISSIONS
            cy.get('[data-test="duplicate-submissions-a"]')
                .find('h5')
                .should('contain', instancesAInfos.instances[0].form_name);
            cy.get('[data-test="duplicate-submissions-b"]')
                .find('h5')
                .should('contain', instancesBInfos.instances[0].form_name);

            cy.get('[data-test="duplicate-submissions-a"]')
                .find('.MuiButtonBase-root')
                .eq(0)
                .click();

            cy.get('[data-test="duplicate-submissions-a"]')
                .find('.MuiCollapse-wrapper .MuiCollapse-wrapperInner table')
                .as('formATable');
            cy.get('@formATable')
                .find('tr')
                .eq(2)
                .find('td')
                .eq(1)
                .should('contain', 'Côté');
            cy.get('@formATable')
                .find('tr')
                .eq(3)
                .find('td')
                .eq(1)
                .should('contain', 'Lauzon');
            cy.get('@formATable')
                .find('tr')
                .eq(4)
                .find('td')
                .eq(1)
                .should('contain', '--');
            cy.get('@formATable')
                .find('tr')
                .eq(5)
                .find('td')
                .eq(1)
                .should('contain', 'Morcel');
            cy.get('@formATable')
                .find('tr')
                .eq(2)
                .find('td')
                .eq(1)
                .should('contain', 'Côté');

            cy.get('[data-test="duplicate-submissions-b"]')
                .find('.MuiButtonBase-root')
                .eq(0)
                .click();

            cy.get('[data-test="duplicate-submissions-b"]')
                .find('.MuiCollapse-wrapper .MuiCollapse-wrapperInner table')
                .as('formBTable');

            cy.get('@formBTable')
                .find('tr')
                .eq(2)
                .find('td')
                .eq(1)
                .should('contain', 'Côté');
            cy.get('@formBTable')
                .find('tr')
                .eq(3)
                .find('td')
                .eq(1)
                .should('contain', 'Gagnon');
            cy.get('@formBTable')
                .find('tr')
                .eq(4)
                .find('td')
                .eq(1)
                .should('contain', '--');
            cy.get('@formBTable')
                .find('tr')
                .eq(5)
                .find('td')
                .eq(1)
                .should('contain', 'Marcel');
        });
    });
    it('action buttons should change duplicate table state', () => {
        mockPage();
        cy.visit(baseUrl);

        cy.wait(['@getDetails', '@getDetailsDuplicate']).then(() => {
            cy.get('#check-box-onlyShowUnmatched').check();
            cy.get('[data-test="duplicate-table"]')
                .find('table')
                .as('duplicateTable');

            cy.get('@duplicateTable')
                .find('tbody')
                .find('[data-test="visible-row"]')
                .as('duplicateTableRows')
                .should('have.length', 2);

            testCellStatus(0, 1, 'diff');
            testCellStatus(0, 2, 'diff');
            testCellIsEmpty(0, 3);
            testCellStatus(1, 1, 'diff');
            testCellStatus(1, 2, 'diff');
            testCellIsEmpty(1, 3);

            cy.get('[data-test="fill-value-a-button"]').click();
            testCellStatus(0, 1, 'selected');
            testCellStatus(0, 2, 'dropped');
            testCellContains(0, 3, 'Lauzon');

            testCellStatus(1, 1, 'selected');
            testCellStatus(1, 2, 'dropped');
            testCellContains(1, 3, 'Marcel');

            cy.get('[data-test="merge-button"]')
                .invoke('attr', 'disabled')
                .should('equal', undefined);

            cy.get('[data-test="fill-value-b-button"]').click();
            testCellStatus(0, 1, 'dropped');
            testCellStatus(0, 2, 'selected');
            testCellContains(0, 3, 'Gagnon');
            testCellStatus(1, 1, 'dropped');
            testCellStatus(1, 2, 'selected');
            testCellContains(1, 3, 'Morcel');
            cy.get('[data-test="merge-button"]')
                .invoke('attr', 'disabled')
                .should('equal', undefined);

            cy.get('[data-test="reset-button"]').click();
            testCellStatus(0, 1, 'diff');
            testCellStatus(0, 2, 'diff');
            testCellIsEmpty(0, 3);
            testCellStatus(1, 1, 'diff');
            testCellStatus(1, 2, 'diff');
            testCellIsEmpty(1, 3);
            cy.get('[data-test="merge-button"]')
                .invoke('attr', 'disabled')
                .should('equal', 'disabled');

            cy.get('@duplicateTableRows')
                .eq(0)
                .find('td')
                .eq(2)
                .find('div')
                .click();
            cy.get('[data-test="fill-value-a-button"]').click();
            testCellStatus(0, 1, 'selected');
            testCellStatus(0, 2, 'dropped');
            testCellContains(0, 3, 'Lauzon');
            testCellStatus(1, 1, 'selected');
            testCellStatus(1, 2, 'dropped');
            testCellContains(1, 3, 'Marcel');
            cy.get('[data-test="merge-button"]')
                .invoke('attr', 'disabled')
                .should('equal', undefined);

            cy.get('[data-test="reset-button"]').click();
            cy.get('@duplicateTableRows')
                .eq(0)
                .find('td')
                .eq(1)
                .find('div')
                .click();
            cy.get('@duplicateTableRows')
                .eq(1)
                .find('td')
                .eq(2)
                .find('div')
                .click();
            testCellStatus(0, 1, 'selected');
            testCellStatus(0, 2, 'dropped');
            testCellContains(0, 3, 'Lauzon');
            testCellStatus(1, 1, 'dropped');
            testCellStatus(1, 2, 'selected');
            testCellContains(1, 3, 'Morcel');
        });
    });

    it('click on merge should send correct info to api', () => {
        mockPage();
        cy.visit(baseUrl);

        cy.wait(['@getDetails', '@getDetailsDuplicate']).then(() => {
            cy.get('[data-test="duplicate-table"]')
                .find('table')
                .as('duplicateTable');

            cy.get('@duplicateTable')
                .find('tbody')
                .find('tr')
                .as('duplicateTableRows')
                .should('have.length', 4);
            cy.get('@duplicateTableRows')
                .eq(0)
                .find('td')
                .eq(1)
                .find('div')
                .click();
            cy.get('@duplicateTableRows')
                .eq(3)
                .find('td')
                .eq(2)
                .find('div')
                .click();

            cy.get('[data-test="merge-button"]')
                .as('mergeButton')
                .invoke('attr', 'disabled')
                .should('equal', undefined);

            interceptFlag = false;
            cy.intercept(
                {
                    method: 'POST',
                    pathname: '/api/entityduplicates',
                },
                req => {
                    interceptFlag = true;
                    req.reply({
                        statusCode: 200,
                        body: {},
                    });
                },
            ).as('mergeDuplicates');
            cy.intercept('GET', '/api/entityduplicates/**/*', {
                fixture: 'duplicates/list-paginated.json',
            });

            cy.intercept(
                'GET',
                '/api/entityduplicates_analyzes/?order=-created_at&limit=1&page=1',
                {
                    fixture: 'duplicates/analysis.json',
                    time: 1000000,
                },
            );
            cy.intercept(
                'GET',
                '/api/entityduplicates_analyzes/?order=-created_at&limit=1&page=1',
                {
                    fixture: 'duplicates/analysis.json',
                    time: 1000000,
                },
            );
            cy.get('@mergeButton').click();

            cy.wait('@mergeDuplicates').then(xhr => {
                cy.wrap(interceptFlag).should('eq', true);
                cy.wrap(xhr.request.body).should('deep.equal', {
                    entity1_id: 883,
                    entity2_id: 163,
                    merge: {
                        What_is_the_father_s_name: 883,
                        caretaker_Last_name: 163,
                    },
                });
            });
        });
    });

    it('click on ignore should send correct info to api', () => {
        mockPage();
        cy.visit(baseUrl);

        cy.wait(['@getDetails', '@getDetailsDuplicate']).then(() => {
            cy.get('[data-test="ignore-button"]')
                .as('ignoreButton')
                .invoke('attr', 'disabled')
                .should('equal', undefined);

            interceptFlag = false;
            cy.intercept(
                {
                    method: 'POST',
                    pathname: '/api/entityduplicates',
                },
                req => {
                    interceptFlag = true;
                    req.reply({
                        statusCode: 200,
                        body: {},
                    });
                },
            ).as('ignoreDuplicates');
            cy.intercept('GET', '/api/entityduplicates/**/*', {
                fixture: 'duplicates/list-paginated.json',
            });

            cy.intercept(
                'GET',
                '/api/entityduplicates_analyzes/?order=-created_at&limit=1&page=1',
                {
                    fixture: 'duplicates/analysis.json',
                    time: 1000000,
                },
            );
            cy.intercept(
                'GET',
                '/api/entityduplicates_analyzes/?order=-created_at&limit=1&page=1',
                {
                    fixture: 'duplicates/analysis.json',
                    time: 1000000,
                },
            );
            cy.get('@ignoreButton').click();

            cy.wait('@ignoreDuplicates').then(xhr => {
                cy.wrap(interceptFlag).should('eq', true);
                cy.wrap(xhr.request.body).should('deep.equal', {
                    entity1_id: 883,
                    entity2_id: 163,
                    ignore: true,
                });
            });
        });
    });
});
