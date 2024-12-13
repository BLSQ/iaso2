import csv
import io
from datetime import timezone
from datetime import datetime

import xlsxwriter  # type: ignore
from django.conf import settings
from django.db.models import QuerySet
from xlsxwriter.utility import xl_rowcol_to_cell  # type: ignore

from hat.common.utils import queryset_iterator


def write_sheet(wb, sheet_name, col_descs, queryset, get_row, sub_columns=None):
    ws = wb.add_worksheet(sheet_name)

    bold = wb.add_format({"bold": True})
    bold.set_text_wrap()
    formats = {"bold": bold, "percent": wb.add_format({"num_format": "0.00%"})}

    advanced = any([1 for cd in col_descs if "format" in cd])
    max_height = max([c["title"].count("\n") for c in col_descs]) + 1  # Nb of lines in titles
    ws.set_row(0, 15 * max_height, bold)  # default height is 15
    ws.freeze_panes(1, 0)

    for i, col_desc in enumerate(col_descs):
        xl_col = xl_rowcol_to_cell(0, i)
        size = col_desc["width"] if "width" in col_desc else len(col_desc["title"])
        col_format = formats.get(col_desc["format"]) if "format" in col_desc else None
        ws.set_column(xl_col + ":" + xl_col, size, col_format)

    row_num = 1
    col_titles = [cd["title"] for cd in col_descs]
    ws.write_row("A" + str(row_num), col_titles, bold)

    if sub_columns:
        row_num += 1
        ws.write_row("A" + str(row_num), sub_columns)

    for item in queryset:
        row_num += 1
        if row_num % 1000 == 0 and settings.DEBUG:
            print(f"Sheet {sheet_name} row {row_num}")

        if not advanced:
            ws.write_row("A" + str(row_num), get_row(item, row_num=row_num))
        else:
            for col_num, column in enumerate(get_row(item, row_num=row_num)):
                cell = xl_rowcol_to_cell(row_num - 1, col_num)
                # The link format is using a text for the link display. Without specific format, a http link
                # will still be automatically colored by Excel but will show the full URL instead of a short text.
                if str(column).startswith("http") and col_descs[col_num].get("format", "") == "link":
                    ws.write_url(cell, str(column), string="Lien")
                else:
                    ws.write(cell, column)


def generate_xlsx(sheet_name, columns, queryset, get_row, sub_columns=None):
    # TODO: document sub_columns parameter
    """
    Generate an XLSX file with the provided parameters.

    Excel requires sheet names to be less or equal to 31 characters:
    https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oi29500/ebf12ea5-2bb4-4af5-ab26-563f22d3f895

    :param sheet_name: Array of sheet names
    :param columns: Array of column descriptors. First array per sheet, second Array per column, then dict. Example
                    [[{"title": "This is the\ntitle", "width": 10}, {"title": "foo"}]]
                    title: Title of the columns, shown in bold in the header row. This can contain crlf to force
                           multiple lines. The row height will be computed depending on the nb of crlf
                    width: roughly equivalent to the number of characters. If unspecified, the length of the title
                           is used.
                    format: format of the content. This is only necessary for "percent" for example
    :param queryset: Array of querysets to use for each sheet
    :param get_row: Array of functions to fetch data values.
                    Minimal version: get_row(row, **kwargs) where row is a queryset item
                    **kwargs allows the XLSX generator to pass additional params without rewriting all get_row methods
                    Additional params include:
                    * row_num that is useful to make basic formulas.
    :return: the XLSX result to be included in the response. This is always using a temporary file.
    """
    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {"constant_memory": True, "remove_timezone": True})
    if isinstance(sheet_name, list):
        i = 0
        for sheet in sheet_name:
            write_sheet(wb, sheet[:31], columns[i], queryset[i], get_row[i])
            i += 1
    else:
        write_sheet(wb, sheet_name[:31], columns, queryset, get_row, sub_columns)

    wb.close()

    output.seek(0)
    return output


class Echo:
    def write(self, value):
        return value


def iter_items(queryset, pseudo_buffer, columns, get_row, chunk_size=5000):
    writer = csv.writer(pseudo_buffer)
    if columns and len(columns) > 0 and type(columns[0]) == dict:
        yield writer.writerow([c["title"].replace("\n", " ") for c in columns])
    else:
        yield writer.writerow(columns)
    if isinstance(queryset, QuerySet):  # type: ignore
        for item in queryset_iterator(queryset, chunk_size=chunk_size):
            yield writer.writerow(get_row(item))
    else:
        for item in queryset:
            yield writer.writerow(get_row(item))


def timestamp_to_utc_datetime(timestamp):
    """iaso mobile app >= 2.0 send timestamp as second instead of microsecond
    so we do a detection  cf https://bluesquare.atlassian.net/browse/IA-1473"""
    dt = datetime.fromtimestamp(int(timestamp / 1000), timezone.utc)
    if dt.year < 1972:
        return datetime.fromtimestamp(int(timestamp), timezone.utc)
    else:
        return dt
