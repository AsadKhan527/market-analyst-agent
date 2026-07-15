"""Renders the structured report JSON into a branded PDF. Perceived value of this
project rides heavily on the PDF looking professional, not on the JSON underneath."""
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, HRFlowable


def render_pdf(report: dict, business_name: str, brand_color: str, output_path: str):
    doc = SimpleDocTemplate(output_path, pagesize=LETTER, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()

    brand = colors.HexColor(brand_color)
    title_style = ParagraphStyle("TitleBrand", parent=styles["Title"], textColor=brand)
    h2 = ParagraphStyle("H2Brand", parent=styles["Heading2"], textColor=brand, spaceBefore=18)
    body = styles["BodyText"]

    story = [
        Paragraph(f"Competitive Market Analysis", title_style),
        Paragraph(f"Prepared for {business_name}", styles["Normal"]),
        Spacer(1, 0.15 * inch),
        HRFlowable(width="100%", color=brand, thickness=1.2),
        Spacer(1, 0.2 * inch),
        Paragraph("Executive Summary", h2),
        Paragraph(report.get("executive_summary", ""), body),
    ]

    for comp in report.get("competitors", []):
        story.append(Paragraph(comp.get("name", "Competitor"), h2))
        story.append(Paragraph(f"<b>Pricing:</b> {comp.get('pricing', 'N/A')}", body))
        story.append(Paragraph(f"<b>Positioning:</b> {comp.get('positioning', 'N/A')}", body))

        if comp.get("strengths"):
            story.append(Paragraph("Strengths:", styles["Heading4"]))
            story.append(ListFlowable([ListItem(Paragraph(s, body)) for s in comp["strengths"]], bulletType="bullet"))
        if comp.get("weaknesses"):
            story.append(Paragraph("Weaknesses:", styles["Heading4"]))
            story.append(ListFlowable([ListItem(Paragraph(w, body)) for w in comp["weaknesses"]], bulletType="bullet"))
        if comp.get("sources"):
            src_text = ", ".join(comp["sources"])
            story.append(Paragraph(f"<font size=8 color='grey'>Sources: {src_text}</font>", body))
        story.append(Spacer(1, 0.1 * inch))

    if report.get("opportunities"):
        story.append(Paragraph("Opportunities", h2))
        story.append(ListFlowable([ListItem(Paragraph(o, body)) for o in report["opportunities"]], bulletType="bullet"))

    if report.get("recommendations"):
        story.append(Paragraph("Recommendations", h2))
        story.append(ListFlowable([ListItem(Paragraph(r, body)) for r in report["recommendations"]], bulletType="bullet"))

    doc.build(story)
    return output_path
