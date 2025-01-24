import logging
import tempfile

import clamav_client
from clamav_client.clamd import CommunicationError
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile


logger = logging.getLogger(__name__)


def scan_uploaded_file_for_virus(uploaded_file: InMemoryUploadedFile):
    # We need a temporary file because the library requires sending disk files (not memory files)
    logger.info(f"Scanning InMemoryUploadedFile {uploaded_file.name} for virus")
    with tempfile.NamedTemporaryFile(mode="wb") as temp_file:
        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)

        temp_file.flush()  # If you don't flush, you send an empty file
        temp_file_path = temp_file.name
        result = _scan_with_clamav(temp_file_path)

    return result


def scan_disk_file_for_virus(file_path: str):
    logger.info(f"Scanning disk file {file_path} for virus")
    return _scan_with_clamav(file_path)


def _scan_with_clamav(file_path: str):
    is_clamav_active = settings.CLAMAV_ACTIVE
    if not is_clamav_active:
        logger.info("ClamAV is not active, skipping scan")
        return True, "ClamAV is not active, skipping scan"

    try:
        scanner = clamav_client.get_scanner(config=settings.CLAMAV_CONFIGURATION)
        scan = scanner.scan(file_path)
        logger.info(f"Scan result: {scan}")

        is_safe = scan.passed
        if scan.state == "FOUND":
            details = f"A virus was found in this file, please contact your administrator"
        elif scan.state == "ERROR":
            details = f"An error occurred while scanning the file - {scan.details}"
        elif scan.state is None:
            details = "The scan is not completed yet"
        else:
            details = ""

        return is_safe, details

    except CommunicationError as e:
        error_message = f"Connection error to ClamAV - {e}"
        logger.error(error_message)
        return False, error_message
    except Exception as e:
        error_message = f"Unknown error while scanning file - {e}"
        logger.error(error_message)
        return False, error_message
