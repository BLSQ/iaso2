/* eslint-disable react/jsx-indent */
import React, { useMemo, useState } from 'react';
import CommentIcon from '@mui/icons-material/Comment';
import FunctionsIcon from '@mui/icons-material/Functions';
import { Table, TableBody, TableCell, TableRow, Tooltip } from '@mui/material';
import { makeStyles } from '@mui/styles';
import { textPlaceholder } from 'bluesquare-components';
import isPlainObject from 'lodash/isPlainObject';
import PropTypes from 'prop-types';

import ImageGallery from '../../../components/dialogs/ImageGalleryComponent.tsx';
import { useLocale } from '../../app/contexts/LocaleContext.tsx';

const useStyle = makeStyles(theme => ({
    tableCellHead: {
        fontWeight: 'bold',
        backgroundColor: theme.palette.gray,
        borderTop: 'none !important',
        borderLeft: 'none !important',
        borderRight: 'none !important',
        borderBottom: `1px solid ${theme.palette.ligthGray.border}  !important`,
    },
    tableCell: {
        backgroundColor: 'transparent',
        borderTop: 'none !important',
        borderLeft: 'none !important',
        borderRight: 'none !important',
        borderBottom: `1px solid ${theme.palette.ligthGray.border}  !important`,
    },
    tableCellCalculated: {
        color: theme.palette.gray.main,
    },
    tableCellLabelWrapper: {
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'center',
    },
    tableCellLabelIcon: {
        alignSelf: 'flex-start',
    },
    tableCellLabel: {
        whiteSpace: 'normal',
        wordBreak: 'break-word',
        marginLeft: 5,
    },
    tableCellLabelName: {
        color: theme.palette.mediumGray.main,
    },
}));

/**
 * Translate the provided label if it is translatable
 * If the locale language matches the user language, we display it
 * if not, we display it in English by default
 * if there is no english version, we display the first one
 * @param label
 * @returns {*}
 */

const labelLocales = { fr: 'French', en: 'English' };

function translateLabel(label, activeLocale) {
    if (isPlainObject(label)) {
        const correctKey = Object.keys(label).find(key => {
            if (labelLocales[activeLocale].includes(key)) {
                return true;
            }
            return labelLocales.en.includes(key);
        });

        if (correctKey) {
            return label[correctKey];
        }
        return label[Object.keys(label)[0]];
    }

    return label;
}

function getRawValue(descriptor, data) {
    const value = data[descriptor.name];
    if (value === undefined) {
        return textPlaceholder;
    }
    return value;
}
/**
 * Extract the value from data using the descriptor
 * (handles the different scenarios, such as select fields)
 *
 * @param descriptor
 * @param data
 * @returns {string|*}
 */
function getDisplayedValue(descriptor, data, activeLocale) {
    const value = data[descriptor.name];
    if (value === undefined) {
        return textPlaceholder;
    }
    switch (descriptor.type) {
        case 'select_one':
        case 'select one': {
            const choice = descriptor.children.find(c => c.name === value);
            return choice !== undefined
                ? translateLabel(choice.label, activeLocale)
                : `${value} (choice not found)`;
        }
        case 'select_multiple':
        case 'select multiple': {
            const choices = descriptor.children.filter(c =>
                value.split(' ').includes(c.name),
            );
            return choices.length > 0
                ? choices
                      .map(choice => translateLabel(choice.label, activeLocale))
                      .join(', ')
                : `${value} (multi choice not found)`;
        }
        default:
            return value !== '' ? value : textPlaceholder;
    }
}

export default function InstanceFileContentRich({
    instanceData,
    formDescriptor,
    showQuestionKey,
    showNote,
    files,
}) {
    return (
        <Table>
            <TableBody>
                {formDescriptor.children
                    .filter(c => c.name !== 'meta')
                    .map(childDescriptor => (
                        <FormChild
                            key={childDescriptor.name}
                            descriptor={childDescriptor}
                            data={instanceData}
                            showQuestionKey={showQuestionKey}
                            showNote={showNote}
                            files={files}
                        />
                    ))}
            </TableBody>
        </Table>
    );
}

InstanceFileContentRich.defaultProps = {
    showQuestionKey: true,
    showNote: true,
    files: [],
};

InstanceFileContentRich.propTypes = {
    instanceData: PropTypes.object.isRequired,
    formDescriptor: PropTypes.object.isRequired,
    showQuestionKey: PropTypes.bool,
    showNote: PropTypes.bool,
    files: PropTypes.arrayOf(PropTypes.string),
};

const PhotoField = ({ descriptor, data, showQuestionKey, files }) => {
    const classes = useStyle();
    const [open, setOpen] = useState(false);

    const value = data[descriptor.name];
    const fileUrl = useMemo(() => {
        if (value && files.length > 0) {
            const slugifiedValue = value.replace(/\s/g, '_'); // Replace spaces with underscores
            return files.find(f => f.includes(slugifiedValue));
        }
        return null;
    }, [value, files]);
    return (
        <TableRow>
            <TableCell className={classes.tableCell}>
                <Label
                    descriptor={descriptor}
                    showQuestionKey={showQuestionKey}
                />
            </TableCell>
            <TableCell
                className={classes.tableCell}
                align="right"
                title={getRawValue(descriptor, data)}
            >
                {value && fileUrl && (
                    <>
                        <img
                            src={fileUrl}
                            alt={descriptor.name}
                            style={{
                                objectFit: 'contain',
                                maxWidth: '35vw',
                                maxHeight: '35vh',
                                cursor: 'pointer',
                                width: '100%',
                                height: 'auto',
                            }}
                            onClick={() => setOpen(true)}
                        />
                        {open && (
                            <ImageGallery
                                closeLightbox={() => setOpen(false)}
                                imageList={[{ path: fileUrl }]}
                                currentIndex={0}
                            />
                        )}
                    </>
                )}
                {(!value || !fileUrl) && textPlaceholder}
            </TableCell>
        </TableRow>
    );
};

PhotoField.defaultProps = {
    showQuestionKey: true,
    files: [],
};

PhotoField.propTypes = {
    descriptor: PropTypes.object.isRequired,
    data: PropTypes.object.isRequired,
    showQuestionKey: PropTypes.bool,
    files: PropTypes.arrayOf(PropTypes.string),
};

function FormChild({ descriptor, data, showQuestionKey, showNote, files }) {
    switch (descriptor.type) {
        case 'repeat':
            return data[descriptor.name]
                ? data[descriptor.name].map(subdata => (
                      <FormGroup
                          key={descriptor.name}
                          descriptor={descriptor}
                          data={subdata}
                          showQuestionKey={showQuestionKey}
                      />
                  ))
                : null;
        case 'group':
            return (
                <FormGroup
                    descriptor={descriptor}
                    data={data}
                    showQuestionKey={showQuestionKey}
                    files={files}
                />
            );
        case 'deviceid':
        case 'subscriberid':
        case 'simserial':
        case 'phonenumber':
            return (
                <FormMetaField
                    descriptor={descriptor}
                    data={data}
                    showQuestionKey={showQuestionKey}
                />
            );
        case 'note':
            return showNote ? (
                <FormNoteField
                    descriptor={descriptor}
                    showQuestionKey={showQuestionKey}
                />
            ) : null;
        case 'photo':
        case 'image':
            return (
                <PhotoField
                    descriptor={descriptor}
                    data={data}
                    showQuestionKey={showQuestionKey}
                    files={files}
                />
            );
        case 'calculate':
            return (
                <FormCalculatedField
                    descriptor={descriptor}
                    data={data}
                    showQuestionKey={showQuestionKey}
                />
            );
        default:
            return (
                <FormField
                    descriptor={descriptor}
                    data={data}
                    showQuestionKey={showQuestionKey}
                />
            );
    }
}

FormChild.defaultProps = {
    showQuestionKey: true,
    showNote: true,
    files: [],
};

FormChild.propTypes = {
    descriptor: PropTypes.object.isRequired,
    data: PropTypes.object.isRequired,
    showQuestionKey: PropTypes.bool,
    showNote: PropTypes.bool,
    files: PropTypes.arrayOf(PropTypes.string),
};

function FormGroup({ descriptor, data, showQuestionKey, files }) {
    const classes = useStyle();

    return (
        <>
            <TableRow>
                <TableCell
                    colSpan={2}
                    align="center"
                    className={classes.tableCellHead}
                >
                    <Label
                        descriptor={descriptor}
                        showQuestionKey={showQuestionKey}
                    />
                </TableCell>
            </TableRow>
            {descriptor.children.map(childDescriptor => (
                <FormChild
                    key={childDescriptor.name}
                    descriptor={childDescriptor}
                    data={data}
                    showQuestionKey={showQuestionKey}
                    files={files}
                />
            ))}
        </>
    );
}

FormGroup.defaultProps = {
    showQuestionKey: true,
    files: [],
};

FormGroup.propTypes = {
    descriptor: PropTypes.object.isRequired,
    data: PropTypes.object.isRequired,
    showQuestionKey: PropTypes.bool,
    files: PropTypes.arrayOf(PropTypes.string),
};

function FormField({ descriptor, data, showQuestionKey }) {
    const classes = useStyle();
    const { locale: activeLocale } = useLocale();

    return (
        <TableRow>
            <TableCell className={classes.tableCell}>
                <Label
                    descriptor={descriptor}
                    showQuestionKey={showQuestionKey}
                />
            </TableCell>
            <TableCell
                className={classes.tableCell}
                align="right"
                title={getRawValue(descriptor, data)}
            >
                {getDisplayedValue(descriptor, data, activeLocale)}
            </TableCell>
        </TableRow>
    );
}

FormField.defaultProps = {
    showQuestionKey: true,
};

FormField.propTypes = {
    descriptor: PropTypes.object.isRequired,
    data: PropTypes.object.isRequired,
    showQuestionKey: PropTypes.bool,
};

function FormCalculatedField({ descriptor, data, showQuestionKey }) {
    const classes = useStyle();
    const { locale: activeLocale } = useLocale();

    return (
        <TableRow>
            <TableCell className={classes.tableCell}>
                <div className={classes.tableCellLabelWrapper}>
                    <FunctionsIcon
                        color="disabled"
                        className={classes.tableCellLabelIcon}
                    />
                    <Label
                        descriptor={descriptor}
                        tooltip={descriptor.bind.calculate}
                        showQuestionKey={showQuestionKey}
                    />
                </div>
            </TableCell>
            <TableCell className={classes.tableCell} align="right">
                {getDisplayedValue(descriptor, data, activeLocale)}
            </TableCell>
        </TableRow>
    );
}

FormCalculatedField.defaultProps = {
    showQuestionKey: true,
};

FormCalculatedField.propTypes = {
    descriptor: PropTypes.object.isRequired,
    data: PropTypes.object.isRequired,
    showQuestionKey: PropTypes.bool,
};

function FormMetaField({ descriptor, data, showQuestionKey }) {
    const classes = useStyle();
    const { locale: activeLocale } = useLocale();

    return (
        <TableRow>
            <TableCell className={classes.tableCell} colSpan={2}>
                <Label
                    descriptor={descriptor}
                    value={getDisplayedValue(descriptor, data, activeLocale)}
                    showQuestionKey={showQuestionKey}
                />
            </TableCell>
        </TableRow>
    );
}

FormMetaField.defaultProps = {
    showQuestionKey: true,
};

FormMetaField.propTypes = {
    descriptor: PropTypes.object.isRequired,
    data: PropTypes.object.isRequired,
    showQuestionKey: PropTypes.bool,
};

function FormNoteField({ descriptor, showQuestionKey }) {
    const classes = useStyle();

    return (
        <TableRow>
            <TableCell className={classes.tableCell} colSpan={2}>
                <div className={classes.tableCellLabelWrapper}>
                    <CommentIcon
                        color="disabled"
                        className={classes.tableCellLabelIcon}
                    />
                    <Label
                        descriptor={descriptor}
                        showQuestionKey={showQuestionKey}
                    />
                </div>
            </TableCell>
        </TableRow>
    );
}

FormNoteField.defaultProps = {
    showQuestionKey: true,
};

FormNoteField.propTypes = {
    descriptor: PropTypes.object.isRequired,
    showQuestionKey: PropTypes.bool,
};

function Label({ descriptor, value, tooltip, showQuestionKey }) {
    const classes = useStyle();
    const { locale: activeLocale } = useLocale();

    let label = descriptor.name;
    let showNameHint = false;
    if ('label' in descriptor) {
        label = translateLabel(descriptor.label, activeLocale);

        if (value !== null) {
            // useful for meta questions, whose labels are like "subscriberid ${subscriberid}"
            label = label.replace(`\${${descriptor.name}}`, value);
        } else {
            showNameHint = true;
        }
    }

    const labelElement = (
        <div className={classes.tableCellLabel}>
            {label.replace(/(<([^>]+)>)/gi, '')}
            {showQuestionKey
                ? showNameHint && (
                      <div className={classes.tableCellLabelName}>
                          {descriptor.name}
                      </div>
                  )
                : null}
        </div>
    );

    return tooltip === null ? (
        labelElement
    ) : (
        <Tooltip size="small" placement="right-start" title={tooltip}>
            {labelElement}
        </Tooltip>
    );
}

Label.defaultProps = {
    value: null,
    tooltip: null,
    showQuestionKey: true,
};

Label.propTypes = {
    descriptor: PropTypes.object.isRequired,
    value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    tooltip: PropTypes.string,
    showQuestionKey: PropTypes.bool,
};
