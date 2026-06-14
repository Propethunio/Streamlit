"""
Narzędzie deweloperskie (uruchamiane lokalnie, NIE w runtime aplikacji).

Generuje domyślny `game_lore.pdf` z treści GAME_CODEX (game_lore.py),
aby kodeks świata był dostępny jako standardowy, czytelny i pobieralny plik PDF.
Uruchom po każdej zmianie GAME_CODEX:  py make_lore_pdf.py

Wymaga reportlab (tylko lokalnie):  py -m pip install reportlab
"""
import re

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from game_lore import GAME_CODEX

OUTPUT = "game_lore.pdf"

# Czcionka z obsługą polskich znaków (wbudowane czcionki reportlab ich nie mają).
pdfmetrics.registerFont(TTFont("Body", r"C:\Windows\Fonts\arial.ttf"))
pdfmetrics.registerFont(TTFont("Body-Bold", r"C:\Windows\Fonts\arialbd.ttf"))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold")

# Emoji nie renderują się w standardowych czcionkach PDF — usuwamy je z wersji PDF.
EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF"
    "\U00002B00-\U00002BFF\U00002190-\U000021FF\U0000FE00-\U0000FE0F]+",
    flags=re.UNICODE,
)


def _clean(s):
    s = EMOJI.sub("", s)
    return re.sub(r"\s{2,}", " ", s).strip()


def _md_bold(s):
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)


styles = getSampleStyleSheet()
H_TITLE = ParagraphStyle("Title", parent=styles["Title"], fontName="Body-Bold",
                         fontSize=26, textColor=HexColor("#5b1fb0"), spaceAfter=2)
H_SUB = ParagraphStyle("Sub", parent=styles["Normal"], fontName="Body",
                       fontSize=12, textColor=HexColor("#888888"), alignment=TA_CENTER, spaceAfter=18)
H_SECTION = ParagraphStyle("Section", parent=styles["Heading2"], fontName="Body-Bold",
                           fontSize=15, textColor=HexColor("#8a2be2"), spaceBefore=14, spaceAfter=6)
P_BODY = ParagraphStyle("Body", parent=styles["Normal"], fontName="Body",
                        fontSize=10.5, leading=15, textColor=HexColor("#1a1a1a"))
P_BULLET = ParagraphStyle("Bullet", parent=P_BODY, leftIndent=14, bulletIndent=2, spaceAfter=3)


def build():
    story = [Paragraph("KODEKS ŚWIATA", H_TITLE), Paragraph("NEON: KRONIKI MROKU", H_SUB)]

    # Bufor bieżącego bloku — łączymy linie zawinięte w źródle w jeden akapit/punkt.
    buf, buf_kind = [], None  # buf_kind: "body" | "bullet"

    def flush():
        nonlocal buf, buf_kind
        if not buf:
            return
        text = _clean(_md_bold(" ".join(buf)))
        if buf_kind == "bullet":
            story.append(Paragraph(text, P_BULLET, bulletText="•"))
        else:
            story.append(Paragraph(text, P_BODY))
        buf, buf_kind = [], None

    for raw in GAME_CODEX.strip().split("\n"):
        stripped = raw.strip()
        if not stripped:
            flush()
            story.append(Spacer(1, 6))
        elif stripped.startswith("## "):
            flush()
            story.append(Paragraph(_clean(stripped[3:]), H_SECTION))
        elif stripped.startswith("- "):
            flush()
            buf, buf_kind = [stripped[2:]], "bullet"
        else:
            # Kontynuacja bieżącego bloku (zawinięta linia) lub nowy akapit.
            if buf_kind is None:
                buf_kind = "body"
            buf.append(stripped)

    flush()

    doc = SimpleDocTemplate(OUTPUT, pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm, title="Kodeks Świata")
    doc.build(story)
    print(f"Zapisano: {OUTPUT}")


if __name__ == "__main__":
    build()
