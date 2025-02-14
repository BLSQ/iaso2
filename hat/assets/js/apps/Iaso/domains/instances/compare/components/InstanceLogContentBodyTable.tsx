import React, { memo } from 'react';
import { TableBody, TableRow, TableCell } from '@mui/material';
import { makeStyles } from '@mui/styles';
import { FileContent } from '../../types/instance';
import { formatLabel } from '../../utils';
import InstanceLogImagePreview from './InstanceLogImagePreview';

type TableBodyProps = {
    fileContent: FileContent;
    fileDescriptor?: Record<string, any>;
};
const useStyles = makeStyles(theme => ({
    tableCell: {
        backgroundColor: 'transparent',
        borderTop: 'none !important',
        borderLeft: 'none !important',
        // @ts-ignore
        borderRight: `1px solid ${theme.palette.ligthGray.border}  !important`,
        // @ts-ignore
        borderBottom: `1px solid ${theme.palette.ligthGray.border}  !important`,
    },
    deletedInfos: {
        color: '#D22B2B !important',
    },
    tableCellLabelName: {
        // @ts-ignore
        color: theme.palette.mediumGray.main,
    },
    highlightedRow: {
        backgroundColor: '#f7eb9c',
    },
}));

const InstanceLogContentBodyTable = memo(
    ({ fileContent, fileDescriptor }: TableBodyProps) => {
        const classes = useStyles();
        const getImageUrl = (value, logFiles) => {
            if (value && logFiles.length > 0) {
                const slugifiedValue = value.replace(/\s/g, '_'); // Replace spaces with underscores
                return logFiles.find(f => f.includes(slugifiedValue));
            }
            return null;
        };

        const renderLogContent = (isImg, question: any, log, logFiles) => {
            if (isImg) {
                return (
                    <InstanceLogImagePreview
                        imageUrl={getImageUrl(
                            log.json[question.name],
                            logFiles,
                        )}
                        altText={question.name}
                    />
                );
            }
            return log.json[question.name];
        };
        return (
            <TableBody>
                {fileContent.logA &&
                    fileContent.logB &&
                    fileContent?.fields.map(question => {
                        const isRelevantQuestion = ![
                            'meta',
                            'instanceID',
                        ].includes(question.name);
                        const hasLogContent =
                            fileContent.logA.json[question.name] ||
                            fileContent.logB.json[question.name];
                        const field = fileDescriptor?.children.find(
                            child => child.name === question.name,
                        );
                        const isValuesDifferent =
                            fileContent.logA.json[question.name] !==
                            fileContent.logB.json[question.name];
                        const isImg = ['img', 'photo'].includes(question.type);
                        if (isRelevantQuestion && hasLogContent) {
                            return (
                                <TableRow
                                    key={question.name}
                                    className={
                                        isValuesDifferent
                                            ? classes.highlightedRow
                                            : undefined
                                    }
                                >
                                    <TableCell
                                        className={classes.tableCell}
                                        align="left"
                                    >
                                        <div>
                                            {fileDescriptor?.children && field
                                                ? formatLabel(field)
                                                : question.name}
                                        </div>
                                        <span
                                            className={
                                                classes.tableCellLabelName
                                            }
                                        >
                                            {question.name}
                                        </span>
                                    </TableCell>

                                    <TableCell
                                        className={classes.tableCell}
                                        align="left"
                                    >
                                        {renderLogContent(
                                            isImg,
                                            question,
                                            fileContent.logA,
                                            fileContent.logAFiles,
                                        )}
                                    </TableCell>
                                    <TableCell
                                        className={classes.tableCell}
                                        align="left"
                                    >
                                        {renderLogContent(
                                            isImg,
                                            question,
                                            fileContent.logB,
                                            fileContent.logBFiles,
                                        )}
                                    </TableCell>
                                </TableRow>
                            );
                        }
                        return null;
                    })}
            </TableBody>
        );
    },
);

export default InstanceLogContentBodyTable;
