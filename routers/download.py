from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from schemas.models import DownloadRequest
from io import BytesIO

# --- Local Utility Imports ---
try:
    from utils.file_utils import export_to_docx, export_to_pdf
except ImportError as e:
    print(f"ERROR: A utility file could not be imported. Error: {e}")
    raise

router = APIRouter()

@router.post("/docx")
async def generate_docx_file(request: DownloadRequest):
    """
    Accepts insight data and generates a downloadable .docx file.
    """
    try:
        buffer, _, _ = export_to_docx(
            records=request.records,
            consolidated_text=request.consolidated_text,
            user_prompt=request.user_prompt
        )

        if not isinstance(buffer, BytesIO):
            raise ValueError("export_to_docx did not return a valid BytesIO buffer.")

        headers = {
            'Content-Disposition': 'attachment; filename="VantageAI_Insight_Report.docx"'
        }

        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers=headers
        )

    except Exception as e:
        print(f"ERROR: Failed to generate DOCX file: {e}")
        return {"error": f"Failed to generate DOCX file: {e}"}
    
@router.post("/pdf")
async def generate_pdf_file(request: DownloadRequest):
    """
    Accepts insight data and generates a downloadable .pdf file.
    """
    try:
        buffer, _, _ = export_to_pdf(
            records=request.records,
            consolidated_text=request.consolidated_text,
            user_prompt=request.user_prompt
        )

        if not isinstance(buffer, BytesIO):
            raise ValueError("export_to_pdf did not return a valid BytesIO buffer.")

        headers = {
            'Content-Disposition': 'attachment; filename="VantageAI_Insight_Report.pdf"'
        }

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers=headers
        )

    except Exception as e:
        print(f"ERROR: Failed to generate PDF file: {e}")
        return {"error": f"Failed to generate PDF file: {e}"}


@router.post("/excel")
async def generate_excel_file(request: DownloadRequest):
    """
    Accepts insight data and generates a downloadable .xlsx Excel file.
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from openpyxl.utils import get_column_letter
        from datetime import datetime
        
        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Vantage AI Report"
        
        # Styling
        header_fill = PatternFill(start_color="1F4788", end_color="1F4788", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True, size=12)
        title_font = Font(size=16, bold=True, color="1F4788")
        
        # Title
        ws['A1'] = 'Vantage AI - Insight Report'
        ws['A1'].font = title_font
        ws.merge_cells('A1:E1')
        ws['A1'].alignment = Alignment(horizontal='center')
        
        # User Prompt section
        ws['A3'] = 'Query:'
        ws['A3'].font = Font(bold=True)
        ws['B3'] = request.user_prompt or "N/A"
        ws.merge_cells('B3:E3')
        
        # Date
        ws['A4'] = 'Generated:'
        ws['A4'].font = Font(bold=True)
        ws['B4'] = datetime.utcnow().strftime('%B %d, %Y at %I:%M %p UTC')
        
        # Consolidated Insights section
        if request.consolidated_text:
            ws['A6'] = 'Consolidated Insights'
            ws['A6'].font = Font(size=14, bold=True, color="1F4788")
            ws.merge_cells('A6:E6')
            
            ws['A7'] = request.consolidated_text
            ws.merge_cells('A7:E7')
            ws['A7'].alignment = Alignment(wrap_text=True, vertical='top')
            ws.row_dimensions[7].height = 100
        
        # Records section
        if request.records and len(request.records) > 0:
            start_row = 9 if request.consolidated_text else 6
            
            ws[f'A{start_row}'] = 'Detailed Records'
            ws[f'A{start_row}'].font = Font(size=14, bold=True, color="1F4788")
            ws.merge_cells(f'A{start_row}:E{start_row}')
            
            # Headers
            header_row = start_row + 1
            headers = ['#', 'Title', 'Summary', 'Date', 'Source']
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=header_row, column=col)
                cell.value = header
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Data rows
            for idx, record in enumerate(request.records, 1):
                row = header_row + idx
                ws.cell(row=row, column=1).value = idx
                ws.cell(row=row, column=2).value = record.get('title', 'N/A')
                ws.cell(row=row, column=3).value = record.get('summary', 'N/A')
                ws.cell(row=row, column=4).value = record.get('record_date', 'N/A')
                ws.cell(row=row, column=5).value = record.get('source_type', 'N/A')
                
                # Wrap text for summary
                ws.cell(row=row, column=3).alignment = Alignment(wrap_text=True, vertical='top')
                ws.row_dimensions[row].height = 60
        
        # Auto-adjust column widths
        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 30
        ws.column_dimensions['C'].width = 60
        ws.column_dimensions['D'].width = 15
        ws.column_dimensions['E'].width = 15
        
        # Save to BytesIO
        excel_buffer = BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        headers = {
            'Content-Disposition': 'attachment; filename="VantageAI_Insight_Report.xlsx"'
        }
        
        return StreamingResponse(
            excel_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
        
    except Exception as e:
        print(f"ERROR: Failed to generate Excel file: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to generate Excel file: {e}"}

