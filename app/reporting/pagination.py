"""Canvas that writes final page totals after layout, including multi-pass contents."""

from reportlab.pdfgen.canvas import Canvas


class NumberedCanvas(Canvas):
    def __init__(self, *args, page_label="Page", of_label="of", **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_pages = []
        self._page_label = page_label
        self._of_label = of_label

    def showPage(self):
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        pages = self._saved_pages
        total = len(pages)
        for state in pages:
            self.__dict__.update(state)
            self.setFont("RF", 7)
            self.setFillColorRGB(0.32, 0.40, 0.47)
            self.drawRightString(
                self._pagesize[0] - 40,
                18,
                f"{self._page_label} {self._pageNumber:02} {self._of_label} {total:02}",
            )
            super().showPage()
        super().save()
