import React from 'react';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { makeStyles } from '@mui/styles';
import { TreeItem, TreeView } from '@mui/x-tree-view';
import _ from 'lodash';
import Descriptor from '../descriptor';

import { isMapped, isNeverMapped } from '../question_mappings';

const useStyles = makeStyles(theme => ({
    root: {
        height: 'calc(100vh - 64px)',
        flexGrow: 1,
        overflow: 'auto',
    },
    mapped: {
        color: 'green',
    },
    neverMapped: {
        color: theme.palette.gray.main,
    },
}));

const RecursiveTreeView = props => {
    const classes = useStyles();
    const { formVersion, mappingVersion, onQuestionSelected } = props;

    const { descriptor } = formVersion;
    const indexedQuestions = Descriptor.indexQuestions(descriptor);

    const onNodeSelected = (event, value) => {
        const val = indexedQuestions[value];
        if (val && val.type !== 'group') {
            onQuestionSelected(val);
        }
    };
    const renderTree = (node, isTopNode = false) => {
        const coverage = Descriptor.getCoverage(
            indexedQuestions,
            mappingVersion,
            node,
            isTopNode,
        );
        const questionMapping =
            mappingVersion.question_mappings[Descriptor.getKey(node)];
        const mapped = isMapped(questionMapping);
        const neverMapped = isNeverMapped(questionMapping);

        const allChidrenMapped =
            Descriptor.hasChildren(node) && coverage[0] === coverage[1];
        let className = '';
        if (neverMapped) {
            className = classes.neverMapped;
        }
        if (mapped || allChidrenMapped) {
            className = classes.mapped;
        }
        let label = _.truncate(Descriptor.getHumanLabel(node));
        if (Descriptor.hasChildren(node)) {
            label = `${label} (${coverage.join(' / ')})`;
        } else if (node.type) {
            label = `${label} (${node.type})`;
        }
        return (
            <TreeItem
                key={Descriptor.getKey(node)}
                nodeId={Descriptor.getKey(node)}
                label={label}
                title={Descriptor.getHumanLabel(node)}
                className={className}
            >
                {Descriptor.hasChildren(node)
                    ? node.children.map(n => renderTree(n))
                    : null}
            </TreeItem>
        );
    };

    return (
        <div className={classes.root}>
            <TreeView
                className={classes.root}
                defaultCollapseIcon={<ExpandMoreIcon />}
                defaultExpanded={[descriptor.name]}
                defaultExpandIcon={<ChevronRightIcon />}
                onNodeSelect={onNodeSelected}
            >
                {renderTree(descriptor, true)}
            </TreeView>
        </div>
    );
};

export default RecursiveTreeView;
