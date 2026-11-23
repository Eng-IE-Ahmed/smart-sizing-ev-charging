"""Small Word (COM) document builder for the  report and paper (no extra packages: Microsoft Word 16 via pywin32).

Blocks: title/author lines, headings, paragraphs with **bold** and *italic* markup, bullet lists, figures with captions,
tables (header shading, font size), page breaks. save() writes .docx and .pdf, returns the page count (Word's own
pagination) and renders every page to PNG (page EMF from Word -> PIL) for visual checks.
Used by scripts/build_report.py and scripts/build_short_paper.py.
"""
import re
from pathlib import Path

import win32com.client as win32
from PIL import Image

CM = 28.3465
WD = dict(normal=-1, h1=-2, h2=-3, h3=-4, title=-63, caption=-35, list_bullet=-49)


class WordDoc:
    def __init__(self, font="Calibri", size=10.5, margins_cm=(2.0, 2.0, 2.0, 2.0), heading_font="Calibri",
                 space_after=4, line_rule=0):
        self.word = win32.DispatchEx("Word.Application")
        self.word.Visible = False
        self.word.DisplayAlerts = 0
        self.doc = self.word.Documents.Add()
        d = self.doc
        ps = d.PageSetup
        ps.PaperSize = 7                                   # A4
        ps.TopMargin, ps.BottomMargin, ps.LeftMargin, ps.RightMargin = [m * CM for m in margins_cm]
        st = d.Styles(WD["normal"])
        st.Font.Name, st.Font.Size = font, size
        st.ParagraphFormat.SpaceBefore, st.ParagraphFormat.SpaceAfter = 0, space_after
        st.ParagraphFormat.LineSpacingRule = line_rule
        for key, sz, before, after in (("h1", size + 3.5, 8, 3), ("h2", size + 1.5, 6, 2), ("h3", size + 0.5, 4, 2)):
            h = d.Styles(WD[key])
            h.Font.Name, h.Font.Size, h.Font.Bold = heading_font, sz, True
            h.Font.Color = 0x784E1F                         # BGR of #1F4E78
            h.ParagraphFormat.SpaceBefore, h.ParagraphFormat.SpaceAfter = before, after
            h.ParagraphFormat.KeepWithNext = True
        cap = d.Styles(WD["caption"])
        cap.Font.Name, cap.Font.Size, cap.Font.Bold, cap.Font.Italic = font, size - 1.5, False, True
        cap.Font.Color = 0x404040
        cap.ParagraphFormat.SpaceAfter = 6
        self.sel = self.word.Selection
        self.nfig = 0
        self.ntab = 0

    # ---------------------------------------------------------------- text
    def _runs(self, text):
        s = self.sel
        for part in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text):
            if not part:
                continue
            if part.startswith("**"):
                s.Font.Bold = True
                s.TypeText(part[2:-2])
                s.Font.Bold = False
            elif part.startswith("*"):
                s.Font.Italic = True
                s.TypeText(part[1:-1])
                s.Font.Italic = False
            else:
                s.TypeText(part)

    def para(self, text, style="normal", align=None, size=None, bold=False, color=None, space_after=None, keep_next=False):
        s = self.sel
        s.Style = self.doc.Styles(WD[style])
        if align is not None:
            s.ParagraphFormat.Alignment = align              # 0 left, 1 center, 2 right, 3 justify
        if space_after is not None:
            s.ParagraphFormat.SpaceAfter = space_after
        if keep_next:
            s.ParagraphFormat.KeepWithNext = True
        if size:
            s.Font.Size = size
        if color is not None:
            s.Font.Color = color
        s.Font.Bold = bold
        self._runs(text)
        s.TypeParagraph()
        s.Font.Bold = False
        s.Font.Color = 0
        if size:
            s.Font.Size = self.doc.Styles(WD["normal"]).Font.Size

    def heading(self, text, level=1):
        self.para(text, style={1: "h1", 2: "h2", 3: "h3"}[level])

    def bullets(self, items, size=None):
        for it in items:
            s = self.sel
            s.Style = self.doc.Styles(WD["list_bullet"])
            if size:
                s.Font.Size = size
            s.ParagraphFormat.SpaceAfter = 1
            self._runs(it)
            s.TypeParagraph()
        self.sel.Style = self.doc.Styles(WD["normal"])

    def page_break(self):
        self.sel.InsertBreak(7)

    # ---------------------------------------------------------------- figures and tables
    def figure(self, path, width_cm, caption, label="Figure"):
        s = self.sel
        s.Style = self.doc.Styles(WD["normal"])
        s.ParagraphFormat.Alignment = 1
        s.ParagraphFormat.KeepWithNext = True
        s.ParagraphFormat.SpaceAfter = 0
        shp = s.InlineShapes.AddPicture(str(Path(path).resolve()))
        shp.LockAspectRatio = True
        shp.Width = width_cm * CM
        s.TypeParagraph()
        self.nfig += 1
        self.para(f"{label} {self.nfig}. {caption}", style="caption", align=1)
        self.sel.ParagraphFormat.Alignment = 3
        return self.nfig

    def image(self, path, width_cm, space_after=6):
        """Centred image without caption (e.g. the university logo on the cover)."""
        s = self.sel
        s.Style = self.doc.Styles(WD["normal"])
        s.ParagraphFormat.Alignment = 1
        s.ParagraphFormat.SpaceAfter = space_after
        shp = s.InlineShapes.AddPicture(str(Path(path).resolve()))
        shp.LockAspectRatio = True
        shp.Width = width_cm * CM
        s.TypeParagraph()

    def table(self, rows, caption=None, font_size=8.5, col_widths_cm=None, header_fill=0xF8EEEE, align_cols=None,
              caption_above=True, label="Table"):
        if caption and caption_above:
            self.ntab += 1
            self.para(f"{label} {self.ntab}. {caption}", style="caption", align=0, keep_next=True, space_after=2)
        s = self.sel
        s.Style = self.doc.Styles(WD["normal"])
        nr, nc = len(rows), len(rows[0])
        t = self.doc.Tables.Add(s.Range, nr, nc)
        t.Borders.Enable = True
        t.Range.Font.Size = font_size
        t.Range.ParagraphFormat.SpaceAfter = 0
        t.Range.ParagraphFormat.Alignment = 0
        t.TopPadding = t.BottomPadding = 0.5
        t.LeftPadding = t.RightPadding = 2.5
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                cell = t.Cell(i + 1, j + 1)
                cell.Range.Text = str(v)
                if align_cols and j in align_cols and i > 0:
                    cell.Range.ParagraphFormat.Alignment = align_cols[j]
        t.Rows(1).Range.Font.Bold = True
        t.Rows(1).Shading.BackgroundPatternColor = header_fill
        t.Rows(1).HeadingFormat = True
        if col_widths_cm:
            for j, w in enumerate(col_widths_cm):
                t.Columns(j + 1).Width = w * CM
        else:
            t.AutoFitBehavior(1)
            t.AutoFitBehavior(2)
        t.Rows.AllowBreakAcrossPages = False
        s.EndKey(6)
        if caption and not caption_above:
            self.ntab += 1
            self.para(f"{label} {self.ntab}. {caption}", style="caption", align=0)
        else:
            self.para("", space_after=2)
        return self.ntab

    # ---------------------------------------------------------------- output
    def footer_page_numbers(self, text=None):
        for sec in self.doc.Sections:
            f = sec.Footers(1)
            f.PageNumbers.Add(1, True)
            if text:
                f.Range.InsertBefore(text)
                f.Range.Font.Size = 8

    def save(self, docx, pdf=None, png_dir=None, png_width=1100):
        docx, pdf = Path(docx).resolve(), Path(pdf).resolve() if pdf else None
        docx.parent.mkdir(parents=True, exist_ok=True)
        self.doc.Repaginate()
        self.doc.SaveAs2(str(docx), 16)
        pages = self.doc.ComputeStatistics(2)
        if pdf:
            self.doc.ExportAsFixedFormat(str(pdf), 17)
        imgs = []
        if png_dir:
            png_dir = Path(png_dir)
            png_dir.mkdir(parents=True, exist_ok=True)
            for old in png_dir.glob("page_*.png"):
                old.unlink()
            win = self.doc.ActiveWindow
            win.View.Type = 3
            for i in range(1, pages + 1):
                bits = win.ActivePane.Pages(i).EnhMetaFileBits
                emf = png_dir / f"page_{i:02d}.emf"
                emf.write_bytes(bytes(bits))
                try:
                    im = Image.open(emf)
                    im.load(dpi=110)
                    im = im.convert("RGB")
                    if im.width > png_width:
                        im = im.resize((png_width, int(im.height * png_width / im.width)))
                    p = png_dir / f"page_{i:02d}.png"
                    im.save(p)
                    imgs.append(p)
                except Exception as e:  # noqa: BLE001
                    print("page render failed", i, e)
                emf.unlink(missing_ok=True)
        return pages, imgs

    def close(self):
        try:
            self.doc.Close(SaveChanges=False)
        finally:
            self.word.Quit()
