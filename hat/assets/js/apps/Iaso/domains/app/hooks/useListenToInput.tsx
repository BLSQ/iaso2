import { Dispatch, SetStateAction, useEffect, useState } from 'react';
import { isEqual } from 'lodash';

const emptyArray = [];

const useListenToKeyboard = (): [
    string[],
    Dispatch<SetStateAction<string[]>>,
] => {
    const [keyList, setKeyList] = useState<string[]>(emptyArray);

    useEffect(() => {
        const update = e => {
            setKeyList(value => {
                return [...value, e.key];
            });
        };
        document.addEventListener('keydown', update);
        return () => {
            document.removeEventListener('keydown', update);
        };
    });

    return [keyList, setKeyList];
};

export const useListenToInput = (combination: string[]): boolean => {
    const [hasCompleted, setHasCompleted] = useState<boolean>(false);
    const [keyList, setKeyList] = useListenToKeyboard();

    useEffect(() => {
        const controlArray = combination.slice(0, keyList.length);
        if (!isEqual(controlArray, keyList) && keyList.length > 0) {
            setKeyList(emptyArray);
        }
    }, [combination, keyList, setKeyList]);

    useEffect(() => {
        if (keyList.length === combination.length) {
            if (isEqual(keyList, combination)) {
                setHasCompleted(true);
            }
        } else {
            setHasCompleted(false);
        }
    }, [combination, keyList]);

    return hasCompleted;
};
