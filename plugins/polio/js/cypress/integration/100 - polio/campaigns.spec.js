/// <reference types='cypress' />
import { testPlugin } from '../../../../../../hat/assets/js/cypress/support/testPlugin';

const { assert } = require('chai');

testPlugin('polio', () => {
    describe('conditional polio test', () => {
        it('test polio', () => {
            assert(true);
        });
    });
});
