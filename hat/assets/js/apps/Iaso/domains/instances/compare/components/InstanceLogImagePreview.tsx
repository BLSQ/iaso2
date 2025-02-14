import React, { useState } from 'react';
import ImageGallery from '../../../../components/dialogs/ImageGalleryComponent';

type ImagePreviewProps = {
    imageUrl: string | null;
    altText: string;
};

const InstanceLogImagePreview: React.FC<ImagePreviewProps> = ({
    imageUrl,
    altText,
}) => {
    const [open, setOpen] = useState(false);

    if (!imageUrl) return null;

    return (
        <>
            <img
                src={imageUrl}
                alt={altText}
                style={{
                    objectFit: 'contain',
                    maxWidth: '35vw',
                    cursor: 'pointer',
                    maxHeight: '35vh',
                    width: '100%',
                    height: 'auto',
                }}
                onClick={() => setOpen(true)}
            />
            {open && (
                <ImageGallery
                    closeLightbox={() => setOpen(false)}
                    imageList={[
                        {
                            path: imageUrl,
                            itemId: 0,
                            createdAt: 0,
                        },
                    ]}
                    currentIndex={0}
                />
            )}
        </>
    );
};

export default InstanceLogImagePreview;
