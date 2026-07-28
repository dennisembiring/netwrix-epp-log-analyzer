"""Export helpers for CSV / Excel / PDF."""

import io

import pandas as pd
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Data") -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        ws = writer.sheets[sheet_name]
        for i, col_name in enumerate(df.columns, start=1):
            max_len = max(
                [len(str(col_name))] + [len(str(v)) for v in df[col_name].head(200)]
            )
            ws.column_dimensions[get_column_letter(i)].width = min(max_len + 2, 60)
    return buf.getvalue()


def _data_table(df: pd.DataFrame, max_rows: int) -> Table:
    shown = df.head(max_rows)
    data = [list(shown.columns)] + shown.astype(str).values.tolist()
    table = Table(data, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b3a55")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
            ]
        )
    )
    return table


def to_pdf_bytes(
    title: str,
    summary_lines: list[str],
    df: pd.DataFrame | None = None,
    max_rows: int = 200,
) -> bytes:
    buf = io.BytesIO()
    # Landscape only pays off for wide tables; narrow summary tables (like the
    # Reports page breakdowns) look lost in all that empty space otherwise.
    col_count = len(df.columns) if df is not None else 0
    page_size = landscape(letter) if col_count > 4 else letter
    doc = SimpleDocTemplate(
        buf, pagesize=page_size, topMargin=0.5 * inch, bottomMargin=0.5 * inch
    )
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.alignment = TA_LEFT
    story = [Paragraph(title, title_style), Spacer(1, 12)]

    for line in summary_lines:
        story.append(Paragraph(line, styles["Normal"]))
    story.append(Spacer(1, 16))

    if df is not None and not df.empty:
        story.append(_data_table(df, max_rows))
        if len(df) > max_rows:
            story.append(Spacer(1, 8))
            story.append(
                Paragraph(
                    f"Menampilkan {max_rows} dari {len(df)} baris.", styles["Normal"]
                )
            )

    doc.build(story)
    return buf.getvalue()


def to_full_report_pdf_bytes(
    title: str,
    summary_lines: list[str],
    sections: list[tuple[str, pd.DataFrame]],
    max_rows: int = 100,
) -> bytes:
    """One PDF combining several labeled summary tables, in filed order."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch
    )
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.alignment = TA_LEFT
    heading_style = styles["Heading2"]
    heading_style.alignment = TA_LEFT

    story = [Paragraph(title, title_style), Spacer(1, 12)]
    for line in summary_lines:
        story.append(Paragraph(line, styles["Normal"]))
    story.append(Spacer(1, 16))

    sections = [(label, df) for label, df in sections if df is not None and not df.empty]
    for i, (label, df) in enumerate(sections):
        story.append(Paragraph(label, heading_style))
        story.append(Spacer(1, 6))
        story.append(_data_table(df, max_rows))
        if i < len(sections) - 1:
            story.append(Spacer(1, 20))

    doc.build(story)
    return buf.getvalue()
