/// <reference types="cypress" />
import { search, searchWithForbiddenChars } from '../../constants/search';
import page2 from '../../fixtures/entities/list-page-2.json';
import listFixture from '../../fixtures/entities/list.json';
import superUser from '../../fixtures/profiles/me/superuser.json';
import { testPagination } from '../../support/testPagination';
import { testSearchField } from '../../support/testSearchField';
import { testTablerender } from '../../support/testTableRender';

const siteBaseUrl = Cypress.env('siteBaseUrl');
const baseUrl = `${siteBaseUrl}/dashboard/entities/list`;

let interceptFlag = false;
const defaultQuery = {
    order_columns: 'last_saved_instance',
    limit: '20',
    page: '1',
    tab: 'list',
};
const mockPage = (
    fakeUser = superUser,
    formQuery,
    fixture = 'entities/list.json',
) => {
    cy.login();
    interceptFlag = false;
    cy.intercept('GET', '/sockjs-node/**');
    cy.intercept('GET', '/api/profiles/me/**', fakeUser);
    cy.intercept('GET', '/api/entitytypes/?order=name', {
        fixture: 'entityTypes/list.json',
    }).as('getEntitiesTypes');
    cy.intercept('GET', '/api/microplanning/teams/*', {
        fixture: 'teams/list.json',
    });
    cy.intercept('GET', '/api/profiles', {
        fixture: 'profiles/list-not-paginated.json',
    });
    const options = {
        method: 'GET',
        pathname: '/api/entities',
    };
    const query = {
        ...defaultQuery,
        ...formQuery,
    };
    cy.intercept({ ...options, query }, req => {
        req.continue(res => {
            interceptFlag = true;
            res.send({ fixture });
        });
    }).as('getEntities');
};

describe('Entities', () => {
    it('Filter button action should deep link search and call api with same params', () => {
        mockPage();
        cy.visit(baseUrl);
        cy.get('[data-test="search-button"]')
            .invoke('attr', 'disabled')
            .should('equal', 'disabled');
        interceptFlag = false;
        cy.intercept(
            {
                method: 'GET',
                pathname: '/api/entities/',
                query: {
                    ...defaultQuery,
                    search,
                    dateFrom: '10-03-2022',
                    dateTo: '20-03-2022',
                    created_by_team_id: '25',
                    created_by_id: '2',
                    orgUnitId: '2',
                },
            },
            req => {
                interceptFlag = true;
                req.reply({
                    statusCode: 200,
                    body: listFixture,
                });
            },
        ).as('getEntities');

        cy.intercept('GET', '/api/profiles', {
            fixture: 'profiles/list-not-paginated.json',
        }).as('getProfiles');
        cy.intercept('GET', '/api/orgunits/3', {
            fixture: 'orgunits/details.json',
        });
        cy.get('#search-search').type(search);
        cy.get('[data-test="start-date"] input').type('10032022');
        cy.get('[data-test="end-date"] input').type('20032022');
        cy.fillSingleSelect('#submitterTeamId', 0);

        cy.wait('@getProfiles').then(() => {
            cy.fillSingleSelect('#submitterId', 0);
            cy.fillTreeView('#ou-tree-input', 2, false);

            cy.get('[data-test="search-button"]').click();
            cy.url().should(
                'contain',
                `/search/${search}/location/3/dateFrom/10-03-2022/dateTo/20-03-2022/submitterId/5/submitterTeamId/25/`,
            );

            cy.wait('@getEntities').then(() => {
                cy.wrap(interceptFlag).should('eq', true);
            });
        });
    });

    it('submitter team and submitter filters should be linked', () => {
        mockPage();
        cy.visit(baseUrl);
        cy.testInputValue('#submitterTeamId', '');
        cy.testInputValue('#submitterId', '');
        cy.fillSingleSelect('#submitterId', 0);
        cy.testInputValue('#submitterId', 'oneFistPunch (Bruce Lee) ');
        cy.intercept('GET', '/api/profiles', {
            fixture: 'profiles/list-not-paginated.json',
        }).as('getProfiles');
        cy.fillSingleSelect('#submitterTeamId', 0);
        cy.wait('@getProfiles').then(() => {
            cy.testInputValue('#submitterId', '');
        });
    });
    describe('Page', () => {
        it('should redirect to url with pagination params', () => {
            mockPage();
            cy.visit(baseUrl);

            cy.wait('@getEntities').then(() => {
                cy.url().should(
                    'eq',
                    `${baseUrl}/accountId/1/order/last_saved_instance/pageSize/20/page/1`,
                );
            });
        });
        it('should not be accessible if user does not have permission', () => {
            mockPage({
                ...superUser,
                permissions: [],
                is_superuser: false,
            });
            cy.visit(baseUrl);
            const errorCode = cy.get('#error-code');
            errorCode.should('contain', '403');
        });
        it.skip('click on a row button should open entity detail page', () => {
            mockPage();

            cy.intercept(
                'GET',
                '/api/entities/?limit=20&order_columns=last_saved_instance&page=1',
                {
                    fixture: 'entities/list.json',
                },
            ).as('getEntitiesTwice');
            cy.visit(baseUrl);

            cy.wait('@getEntitiesTwice').then(() => {
                cy.get('table tbody tr')
                    .eq(1)
                    .find('td')
                    .last()
                    .as('actionCell');
                cy.get('@actionCell')
                    .find('a')
                    .should(
                        'have.attr',
                        'href',
                        '/dashboard/entities/details/entityId/2',
                    );
            });
        });
    });

    describe('Search field', () => {
        beforeEach(() => {
            mockPage();
            cy.visit(baseUrl);
        });
        testSearchField(search, searchWithForbiddenChars);
    });

    describe('Search button', () => {
        beforeEach(() => {
            mockPage();
            cy.visit(baseUrl);
        });
        it('should be disabled', () => {
            cy.wait('@getEntities').then(() => {
                cy.get('[data-test="search-button"]')
                    .invoke('attr', 'disabled')
                    .should('equal', 'disabled');
            });
        });
        it('should be enabled while searching', () => {
            cy.get('#search-search').type(search);
            cy.wait('@getEntities').then(() => {
                cy.get('[data-test="search-button"]')
                    .invoke('attr', 'disabled')
                    .should('equal', undefined);
            });
        });

        it('action should deep link search', () => {
            cy.wait(['@getEntities', '@getEntitiesTypes']).then(() => {
                cy.get('#search-search').type(search);

                cy.get('[data-test="search-button"]').click();
                cy.url().should(
                    'contain',
                    `${baseUrl}/accountId/1/search/${search}/`,
                );
            });
        });
    });

    describe('Table', () => {
        beforeEach(() => {
            mockPage();
            cy.intercept(
                'GET',
                '/api/entities/?order_columns=last_saved_instance&limit=20&page=1&tab=list',
                {
                    fixture: 'entities/list.json',
                },
            ).as('getEntities');
            cy.intercept(
                'GET',
                '/api/entities/?order_columns=last_saved_instance',
                {
                    fixture: 'entities/list-not-paginated.json',
                },
            );
            cy.intercept(
                {
                    pathname: '/api/entities/',
                    query: {
                        page: '2',
                        limit: '20',
                        order_columns: 'last_saved_instance',
                        tab: 'list',
                    },
                },
                page2,
            );
            cy.visit(baseUrl);
            cy.wait('@getEntities');
        });
        testTablerender({
            baseUrl,
            rows: 20,
            columns: 6,
            apiKey: 'entities',
            withVisit: false,
        });
        testPagination({
            baseUrl,
            apiPath: '/api/entities/**',
            apiKey: 'result',
            withSearch: false,
            fixture: listFixture,
            query: {
                page: '1',
                limit: '20',
                order_columns: 'last_saved_instance',
            },
        });
    });
});
