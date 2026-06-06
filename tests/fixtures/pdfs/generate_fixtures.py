"""Generate minimal test fixture PDFs for OCR and ingestion tests."""
from pathlib import Path
from fpdf import FPDF

OUT = Path(__file__).parent


def make_question_paper() -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Pearson Edexcel IAL Mathematics", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "Pure Mathematics 1 - WME01 - January 2023", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.cell(0, 10, "1. Find the value of x such that 2x + 5 = 13.", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "                                                [2 marks]", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.cell(0, 10, "2. Differentiate f(x) = 3x^2 + 2x - 7 with respect to x.", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "                                                [3 marks]", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.cell(0, 10, "3. Prove that the sum of two odd numbers is always even.", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "                                                [4 marks]", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.cell(0, 10, "(a) Sketch the curve y = sin(x) for 0 <= x <= 2pi.", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "                                                [2 marks]", new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(OUT / "sample_question_paper.pdf"))
    print("Created sample_question_paper.pdf")


def make_mark_scheme() -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Mark Scheme - WME01 - January 2023", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.cell(0, 10, "Question 1", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "M1: Rearrange equation: 2x = 13 - 5 = 8", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "A1: x = 4", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.cell(0, 10, "Question 2", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "M1: Apply power rule to 3x^2: 6x", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "A1: Differentiate 2x: 2", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "A1: f'(x) = 6x + 2", new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(OUT / "sample_mark_scheme.pdf"))
    print("Created sample_mark_scheme.pdf")


def make_examiner_report() -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Examiner's Report - WME01 - January 2023", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.cell(0, 10, "Question 1", new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(
        0, 8,
        "Many candidates correctly rearranged the equation. "
        "Some students made an error in the subtraction step.",
    )
    pdf.ln(3)
    pdf.cell(0, 10, "Question 2", new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(
        0, 8,
        "Most students successfully differentiated 3x^2. "
        "However, some candidates showed a misconception about the constant term.",
    )
    pdf.output(str(OUT / "sample_examiner_report.pdf"))
    print("Created sample_examiner_report.pdf")


if __name__ == "__main__":
    make_question_paper()
    make_mark_scheme()
    make_examiner_report()
