"""PDF generation utilities using reportlab with DejaVu (Cyrillic support)."""
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_FONT_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def _register_fonts():
    try:
        from reportlab.pdfbase.pdfmetrics import registerFontFamily
        pdfmetrics.registerFont(TTFont("DejaVu", _FONT_PATH))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", _FONT_BOLD_PATH))
        registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold",
                           italic="DejaVu", boldItalic="DejaVu-Bold")
        return True
    except Exception:
        return False

_FONTS_OK = _register_fonts()
FONT      = "DejaVu"      if _FONTS_OK else "Helvetica"
FONT_BOLD = "DejaVu-Bold" if _FONTS_OK else "Helvetica-Bold"

def _style(name=None, size=9):
    return ParagraphStyle("s", fontName=name or FONT, fontSize=size, leading=size + 3)

def _bold(text, size=9):
    return Paragraph(text, ParagraphStyle("b", fontName=FONT_BOLD, fontSize=size, leading=size + 3))

def _cell(text, size=9):
    return Paragraph(str(text) if text is not None else "—", _style(size=size))

def _base_table_style():
    return TableStyle([
        ("FONTNAME",    (0, 0), (-1, -1), FONT),
        ("FONTNAME",    (0, 0), (-1, 0),  FONT_BOLD),
        ("FONTSIZE",    (0, 0), (-1, -1), 8),
        ("BACKGROUND",  (0, 0), (-1, 0),  colors.HexColor("#E8EAF6")),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])


# ─────────────────────────────────────────────
# 1. Журнал прихода (Supply)
# ─────────────────────────────────────────────
def generate_supply_pdf(supply) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = []

    story.append(Paragraph("Приходный ордер", ParagraphStyle(
        "title", fontName=FONT_BOLD, fontSize=14, spaceAfter=4)))
    story.append(Paragraph(
        f"Накладная № {supply.invoice_number}  |  "
        f"Дата: {supply.invoice_date}  |  "
        f"Поставщик: {supply.supplier.name if supply.supplier else '—'}  |  "
        f"Статус: {supply.status.value}",
        _style(size=9)))
    if supply.manufacturer:
        story.append(Paragraph(f"Производитель: {supply.manufacturer.name}", _style(size=9)))
    story.append(Spacer(1, 0.4*cm))

    headers = ["№", "Наименование", "Кол-во", "Кол-во мест", "Серия", "Ид. номер", "Дата изг.", "Годен до", "Примечание"]
    col_widths = [1*cm, 6*cm, 2*cm, 2.5*cm, 2.5*cm, 3*cm, 2.5*cm, 2.5*cm, 3.5*cm]

    data = [headers]
    for i, item in enumerate(supply.items, 1):
        data.append([
            str(i),
            item.product.name if item.product else "—",
            str(item.quantity),
            str(item.package_count) if item.package_count else "—",
            item.batch_code or "—",
            item.identification_number or "—",
            item.manufacture_date or "—",
            item.expiry_date.strftime("%d.%m.%Y") if item.expiry_date else "—",
            item.notes or "—",
        ])

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(_base_table_style())
    story.append(t)

    doc.build(story)
    return buf.getvalue()


# ─────────────────────────────────────────────
# 2. Лимитно-заборная карта (ЛЗК)
# ─────────────────────────────────────────────
MONTHS_RU = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
             "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

def generate_limit_card_pdf(card) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = []

    month_name = MONTHS_RU[card.month] if 1 <= card.month <= 12 else str(card.month)
    story.append(Paragraph("Лимитно-заборная карта", ParagraphStyle(
        "title", fontName=FONT_BOLD, fontSize=14, spaceAfter=4)))
    story.append(Paragraph(
        f"Подразделение: {card.department}  |  "
        f"Период: {month_name} {card.year}  |  "
        f"Статус: {'Открыта' if card.status.value == 'open' else 'Закрыта'}",
        _style(size=9)))
    story.append(Spacer(1, 0.4*cm))

    # Лимиты
    if card.allocations:
        story.append(Paragraph("Утверждённые лимиты:", ParagraphStyle(
            "h", fontName=FONT_BOLD, fontSize=10, spaceAfter=3)))
        alloc_data = [["Наименование товара", "Лимит"]]
        for a in card.allocations:
            alloc_data.append([
                a.product.name if a.product else "—",
                str(a.limit_quantity),
            ])
        at = Table(alloc_data, colWidths=[12*cm, 4*cm], repeatRows=1)
        at.setStyle(_base_table_style())
        story.append(at)
        story.append(Spacer(1, 0.4*cm))

    # Операции
    story.append(Paragraph("Операции отпуска:", ParagraphStyle(
        "h", fontName=FONT_BOLD, fontSize=10, spaceAfter=3)))
    headers = ["№", "Дата", "Наименование", "Кол-во", "Примечание"]
    col_widths = [1*cm, 3*cm, 8*cm, 2.5*cm, 4*cm]
    data = [headers]
    for i, item in enumerate(card.items, 1):
        data.append([
            str(i),
            item.operation_date.strftime("%d.%m.%Y") if item.operation_date else "—",
            item.product.name if item.product else "—",
            str(item.quantity),
            item.notes or "—",
        ])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(_base_table_style())
    story.append(t)

    doc.build(story)
    return buf.getvalue()


# ─────────────────────────────────────────────
# 3. Требование-накладная (MaterialRequest)
# ─────────────────────────────────────────────
def generate_request_pdf(req) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = []

    status_map = {"pending": "Ожидает", "approved": "Одобрена", "rejected": "Отклонена"}
    story.append(Paragraph("Требование-накладная", ParagraphStyle(
        "title", fontName=FONT_BOLD, fontSize=14, spaceAfter=4)))
    story.append(Paragraph(
        f"№ {req.id}  |  "
        f"Подразделение: {req.department}  |  "
        f"Статус: {status_map.get(req.status.value, req.status.value)}  |  "
        f"Дата: {req.created_at.strftime('%d.%m.%Y') if req.created_at else '—'}",
        _style(size=9)))
    if req.created_by:
        story.append(Paragraph(f"Составил: {req.created_by.full_name}", _style(size=9)))
    if req.approved_by:
        story.append(Paragraph(f"Утвердил: {req.approved_by.full_name}", _style(size=9)))
    if req.notes:
        story.append(Paragraph(f"Примечание: {req.notes}", _style(size=9)))
    if req.reject_reason:
        story.append(Paragraph(f"Причина отклонения: {req.reject_reason}", _style(size=9)))
    story.append(Spacer(1, 0.4*cm))

    headers = ["№", "Наименование", "Единица", "Количество", "Примечание"]
    col_widths = [1*cm, 9*cm, 2.5*cm, 2.5*cm, 4*cm]
    data = [headers]
    for i, item in enumerate(req.items, 1):
        data.append([
            str(i),
            item.product.name if item.product else "—",
            item.product.unit.value if item.product else "—",
            str(item.quantity),
            item.notes or "—",
        ])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(_base_table_style())
    story.append(t)

    # Подписи
    story.append(Spacer(1, 1.5*cm))
    sig_data = [
        ["Отпустил: _______________", "Получил: _______________"],
    ]
    sig_t = Table(sig_data, colWidths=[9*cm, 9*cm])
    sig_t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), FONT), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story.append(sig_t)

    doc.build(story)
    return buf.getvalue()
