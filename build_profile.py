"""Rebuild the fictional three-page business profile; no API or network needed."""
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

ROOT = Path(__file__).resolve().parent
SUMMARY = """Cedar & Compass Travel is a fictional boutique travel agency based in Hamra, Beirut, Lebanon. Its tagline is "Trips planned by people who've actually been there." Its mission is to make well-planned, stress-free travel across the Mediterranean and the Middle East accessible to young professionals, students and families, with honest pricing and real human expertise behind every itinerary. Its unique value proposition: every itinerary is reviewed by a founder who has personally traveled the route, plus a 24/7 human hotline during your trip.

Services include Custom Itinerary Design (day-by-day plans around budget and interests); Flight + Hotel Packages; Group & Student Trips (discounted group travel and study-abroad travel support); Visa & Documentation Guidance (checklists and appointment help, guidance only and not legal advice); and 24/7 Trip Support for active trips. Fictional sample packages, per person with double occupancy and flights included, are Istanbul City Break, 4 nights, from $620; Athens & Santorini, 6 nights, from $1,150; Barcelona Explorer, 5 nights, from $980; and Cairo & Nile Classic, 7 nights, from $1,320. Custom itinerary design costs $60, credited toward booking. The group/student discount is 10% for groups of 6+. A team member confirms prices, availability, discounts and booking details; no booking or visa outcome is guaranteed.

The fictional team comprises Karim Haddad, Co-founder & Head of Itineraries (12 years in travel, ex-airline operations, 40+ countries visited); Nour Saade, Co-founder & Head of Customer Experience (hospitality management background, leads the 24/7 trip-support team); and Rami Khoury, Partnerships Manager (hotel and airline relationships). The office is in Hamra, Beirut, at a fictional address. Office hours in Beirut time are Monday-Friday 9:00-18:00 and Saturday 10:00-14:00. The hotline operates 24/7 during active trips. Contact hello@cedarcompass-travel.example or +961 1 000 000; these are clearly fake classroom contact details.

To book, share a name, email and short trip note so the team can prepare and confirm a proposal. A 20% deposit confirms a booking after team confirmation, with the balance due 30 days before departure. A free date change is offered up to 45 days before departure; cancellation refunds depend on supplier rules. Visa support is general guidance only: consult official embassy sources and a team member. If a flight is cancelled during an active trip, contact the 24/7 support team; the team will help coordinate with suppliers, and any refund or alternative depends on supplier rules. Do not share passport numbers, payment card details or passwords in the chat.
"""


def build():
    folder = ROOT / "me"
    folder.mkdir(exist_ok=True)
    (folder / "business_summary.txt").write_text(SUMMARY, encoding="utf-8")
    teal = colors.HexColor("#134C4A")
    ink = colors.HexColor("#263C45")
    muted = colors.HexColor("#56666B")
    gold = colors.HexColor("#B88242")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Brand", fontName="Helvetica-Bold", fontSize=27, leading=31, textColor=teal, spaceAfter=12))
    styles.add(ParagraphStyle(name="Section", fontName="Helvetica-Bold", fontSize=17, leading=22, textColor=teal, spaceBefore=14, spaceAfter=10))
    styles.add(ParagraphStyle(name="Copy", fontName="Helvetica", fontSize=10.5, leading=16, textColor=ink, spaceAfter=10))
    styles.add(ParagraphStyle(name="SmallCopy", fontName="Helvetica", fontSize=9, leading=13, textColor=muted, spaceAfter=8))
    styles.add(ParagraphStyle(name="Kicker", fontName="Helvetica-Bold", fontSize=9, leading=13, textColor=gold, spaceAfter=12))
    story = []

    def p(text, style="Copy"):
        story.append(Paragraph(text, styles[style]))

    def section(title):
        p(title, "Section")

    p("FICTIONAL BUSINESS PROFILE  /  EECE 503P/798S", "Kicker")
    p("Cedar &amp; Compass<br/>Travel", "Brand")
    p("Trips planned by people who've actually been there.", "Copy")
    p("Boutique travel agency  |  Hamra, Beirut, Lebanon", "SmallCopy")
    section("Travel with a human touch")
    p("Our mission is to make well-planned, stress-free travel across the Mediterranean and the Middle East accessible to young professionals, students and families, with honest pricing and real human expertise behind every itinerary.")
    section("Our unique value proposition")
    p("Every itinerary is reviewed by a founder who has personally traveled the route, plus a 24/7 human hotline during your trip.")
    section("How we help")
    for heading, body in [
        ("Custom Itinerary Design", "Day-by-day plans built around your budget and interests."),
        ("Flight + Hotel Packages", "Bundled deals for popular destinations."),
        ("Group &amp; Student Trips", "Discounted group travel and study-abroad travel support."),
        ("Visa &amp; Documentation Guidance", "Checklists and appointment help. General guidance only; not legal advice."),
        ("24/7 Trip Support", "A human hotline during every active trip.")]:
        p(f"<b>{heading}</b><br/>{body}")
    p("Classroom simulation: all business identities, offers and contact details in this profile are fictional.", "SmallCopy")
    story.append(PageBreak())

    p("CEDAR &amp; COMPASS TRAVEL  /  OUR OFFERS &amp; PEOPLE", "Kicker")
    section("A few places to start")
    p("Fictional sample prices are per person, based on double occupancy, with flights included. These are starting prices; a team member confirms all pricing, availability and booking details.")
    rows = [["Sample package", "Nights", "From / person"],
            ["Istanbul City Break", "4", "$620"],
            ["Athens & Santorini", "6", "$1,150"],
            ["Barcelona Explorer", "5", "$980"],
            ["Cairo & Nile Classic", "7", "$1,320"]]
    table = Table(rows, colWidths=[257, 70, 144], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), teal), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#EDF4F2"), colors.white]),
        ("LINEBELOW", (0, -1), (-1, -1), 0.6, colors.HexColor("#C8D9D5"))]))
    story.append(table)
    story.append(Spacer(1, 14))
    p("<b>Custom itinerary design:</b> $60, credited toward booking.<br/><b>Group/student discount:</b> 10% for groups of 6+, with the team confirming the actual booking terms.")
    section("Meet the team")
    p("<b>Karim Haddad</b> - Co-founder &amp; Head of Itineraries<br/>12 years in travel, previously in airline operations, and 40+ countries visited.")
    p("<b>Nour Saade</b> - Co-founder &amp; Head of Customer Experience<br/>A hospitality management background; leads the 24/7 trip-support team.")
    p("<b>Rami Khoury</b> - Partnerships Manager<br/>Manages hotel and airline relationships.")
    p("Every team profile and package on this page is fictional.", "SmallCopy")
    story.append(PageBreak())

    p("CEDAR &amp; COMPASS TRAVEL  /  THE PRACTICAL DETAILS", "Kicker")
    section("Booking, payments and changes")
    p("Share your name, email and a short trip note. The team prepares and confirms a proposal. A 20% deposit confirms the booking after team confirmation; the balance is due 30 days before departure.")
    p("A free date change is offered up to 45 days before departure. Cancellation refunds depend on supplier rules. A team member confirms all booking, discount and refund details; visa outcomes are never guaranteed.")
    section("Frequently asked questions")
    faq = [
        ("How do I start a booking?", "Tell us your trip interests, name and email. A team member will confirm the proposal and next steps."),
        ("How much is the deposit?", "20% to confirm, with the balance due 30 days before departure."),
        ("Can you help with visas?", "We provide general checklists and appointment help, not legal advice or a visa guarantee. Consult official embassy sources for requirements."),
        ("Are there group discounts?", "The published group/student discount is 10% for groups of 6+. The team confirms eligibility and the booking details."),
        ("What if my flight is cancelled?", "During an active trip, contact our 24/7 hotline. The team helps coordinate with suppliers. Refunds or alternatives depend on supplier rules; none can be promised in advance.")]
    for q, a in faq:
        p(f"<b>{q}</b><br/>{a}")
    section("Talk to our team")
    p("<b>Office:</b> Hamra, Beirut (fictional address).<br/><b>Office hours:</b> Monday-Friday 9:00-18:00; Saturday 10:00-14:00, Beirut time.<br/><b>Trip hotline:</b> 24/7 for active trips.<br/><b>Email:</b> hello@cedarcompass-travel.example<br/><b>Phone:</b> +961 1 000 000")
    p("Contact details are intentionally fake. Never share passport numbers, payment card details or passwords in chat.", "SmallCopy")

    def page_footer(canvas, doc):
        canvas.setStrokeColor(teal)
        canvas.setLineWidth(0.6)
        canvas.line(62, 48, A4[0] - 62, 48)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(muted)
        canvas.drawString(62, 33, "CEDAR & COMPASS TRAVEL  |  FICTIONAL CLASSROOM BUSINESS")
        canvas.drawRightString(A4[0] - 62, 33, str(doc.page))

    doc = SimpleDocTemplate(str(folder / "about_business.pdf"), pagesize=A4,
        rightMargin=62, leftMargin=62, topMargin=52, bottomMargin=62,
        title="Cedar & Compass Travel - Fictional Business Profile", author="Cedar & Compass Travel (fictional)")
    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    print("Created me/about_business.pdf and me/business_summary.txt")


if __name__ == "__main__":
    build()
