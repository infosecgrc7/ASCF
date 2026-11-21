"""Canonical single-sheet XLSX export and independent saved-file reconciliation."""
import os
from pathlib import Path
import re
import tempfile
from .common import DataError, require
from .ledger import COLUMNS, validate


def verify_workbook(filename, expected_rows):
    import openpyxl
    wb = openpyxl.load_workbook(filename, read_only=False, data_only=False, keep_links=False)
    try:
        require(wb.sheetnames == ['STRM Mapping'], 'Workbook must contain exactly one STRM Mapping sheet')
        ws = wb.active
        require(ws.sheet_state == 'visible' and not ws.merged_cells.ranges, 'Hidden/merged output is not supported')
        require(ws.max_column == 10 and ws.max_row == len(expected_rows) + 1, 'Workbook dimensions differ from canonical output')
        require(not ws.sheet_format.zeroHeight, 'Default row visibility is hidden')
        for dimension in ws.column_dimensions.values():
            if (dimension.min or 1) <= 10:
                require(not dimension.hidden and (dimension.width is None or dimension.width > 0), 'Hidden or zero-width output column')
        for rowno in range(1, len(expected_rows) + 2):
            dimension = ws.row_dimensions[rowno]
            require(not dimension.hidden and (dimension.height is None or dimension.height > 0), 'Hidden or zero-height output row')
        require([cell.value for cell in ws[1]] == COLUMNS, 'Workbook column names/order differ')
        require(len(ws.conditional_formatting) == 0, 'Conditional formatting can obscure canonical output')
        for cell in ws[1]:
            require(cell.font.color is not None and cell.font.color.type == 'rgb'
                    and cell.font.color.rgb[-6:].upper() == 'FFFFFF'
                    and cell.fill.fgColor.type == 'rgb' and cell.fill.fgColor.rgb[-6:].upper() == '173B53',
                    'Header style differs from readable canonical style')
        for rowno, expected in enumerate(expected_rows, 2):
            for colno, name in enumerate(COLUMNS, 1):
                cell = ws.cell(rowno, colno)
                value = cell.value
                require(cell.data_type != 'f' and cell.hyperlink is None, 'Formula/hyperlink in literal mapping data')
                require(cell.font.color is not None and cell.font.color.type == 'rgb'
                        and cell.font.color.rgb[-6:].upper() == '172F42', 'Output text color differs from readable canonical style')
                require(cell.number_format == ('0' if name == 'Strength of Relationship' else 'General'),
                        'Cell display format differs from canonical output')
                target = expected[name]
                if target == '':
                    require(value in (None, ''), 'Nonblank no-match cell: ' + name)
                else:
                    require(type(value) is not bool and value == target, 'Saved cell differs at ' + cell.coordinate)
                    if name == 'Strength of Relationship':
                        require(type(value) in (int, float), 'Strength must be numeric')
                    else:
                        require(isinstance(value, str), 'Text/ID cell was coerced: ' + cell.coordinate)
        return {'status': 'SAVED_XLSX_VERIFIED', 'sheets': 1, 'columns': 10, 'rows': len(expected_rows),
                'formulas': 0, 'source_values_preserved': True}
    finally:
        wb.close()


def build_workbook(doc, catalog, inventory, filename, catalog_hash, inventory_hash, template=None):
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    result, rows = validate(doc, catalog, inventory, catalog_hash, inventory_hash)
    require(result['status'] == 'READY_FOR_EXPORT', 'Ledger blocked: ' + '; '.join(result['errors']))
    target = Path(filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    require(target.suffix.lower() == '.xlsx', 'Output must be .xlsx')
    if template:
        require(Path(template).resolve() != target.resolve(), 'Output must not overwrite its source template')
        wb = openpyxl.load_workbook(template, keep_links=False)
        ws = wb.active
        require([ws.cell(1, i).value for i in range(1, 11)] == COLUMNS, 'Template must have the canonical ten headers on row 1')
        require(ws.max_column == 10 and not ws.merged_cells.ranges, 'Template must be ten unmerged columns')
        for other in list(wb.worksheets):
            if other is not ws:
                wb.remove(other)
        ws.delete_rows(2, ws.max_row)
        for table in list(ws.tables):
            del ws.tables[table]
        ws.title = 'STRM Mapping'
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'STRM Mapping'
    temporary = None
    try:
        from openpyxl.formatting.formatting import ConditionalFormattingList
        ws.conditional_formatting = ConditionalFormattingList()
        ws.sheet_format.zeroHeight = False
        for dimension in ws.row_dimensions.values():
            dimension.hidden = False
            dimension.collapsed = False
            dimension.outlineLevel = 0
        for dimension in ws.column_dimensions.values():
            dimension.hidden = False
            dimension.collapsed = False
            dimension.outlineLevel = 0
        ws.sheet_view.rightToLeft = True
        ws.freeze_panes = 'A2'
        ws.sheet_view.showGridLines = False
        ws.print_title_rows = '1:1'
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.paperSize = ws.PAPERSIZE_A3
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.row_dimensions[1].height = 34
        widths = [17, 29, 64, 18, 22, 36, 17, 76, 20, 78]
        for i, name in enumerate(COLUMNS, 1):
            cell = ws.cell(1, i, name)
            cell.font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='173B53')
            cell.alignment = Alignment(wrap_text=True, vertical='center')
            ws.column_dimensions[get_column_letter(i)].width = widths[i-1]
        for rowno, record in enumerate(rows, 2):
            maximum = 1
            for colno, name in enumerate(COLUMNS, 1):
                value = record[name]
                cell = ws.cell(rowno, colno)
                if isinstance(value, str):
                    require(len(value) <= 32767, 'Excel text length exceeded; no silent truncation: ' + name)
                    cell.value = value
                    # Strings beginning '=', '+', '-' or '@' remain literal, not executable formulas.
                    cell.data_type = 's'
                else:
                    cell.value = value
                cell.font = Font(name='Calibri', size=11, color='172F42')
                cell.fill = PatternFill('solid', fgColor='F1F5F8' if rowno % 2 == 0 else 'FFFFFF')
                rtl = isinstance(value, str) and bool(re.search('[\u0600-\u06ff]', value))
                cell.alignment = Alignment(wrap_text=True, vertical='top', horizontal='right' if rtl else 'left', readingOrder=2 if rtl else 1)
                cell.border = Border(bottom=Side(style='hair', color='D1DCE3'))
                cell.number_format = '0' if name == 'Strength of Relationship' else 'General'
                maximum = max(maximum, len(str(value)) // max(1, widths[colno-1] - 2) + str(value).count('\n') + 1)
            ws.row_dimensions[rowno].height = min(210, max(54, 15 * maximum))
        from openpyxl.worksheet.filters import AutoFilter
        ws.auto_filter = AutoFilter(ref='A1:J' + str(len(rows) + 1))
        ws.sheet_properties.filterMode = False
        ws.print_options.horizontalCentered = True
        ws.print_area = 'A1:J' + str(len(rows) + 1)
        wb.properties.creator = 'SCF Mapping Toolkit'
        wb.properties.title = 'STRM Mapping'
        wb.properties.description = 'Version-pinned mapping output; independent review attestations are retained in the separate ledger.'
        handle, temporary = tempfile.mkstemp(suffix='.xlsx', dir=target.parent)
        os.close(handle)
        wb.save(temporary)
        verification = verify_workbook(temporary, rows)
        os.replace(temporary, target)
        temporary = None
        return verification
    finally:
        wb.close()
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
