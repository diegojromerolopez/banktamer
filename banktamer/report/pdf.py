import math
import os
from fpdf import FPDF
from banktamer.analytics import MonthReport


class PDFReporter(FPDF):
    """Generate a high-quality PDF financial report."""

    def header(self) -> None:
        """Render the PDF header with logo and title."""
        if os.path.exists("assets/logo.png"):
            self.image("assets/logo.png", 10, 8, 33)
        self.set_font("helvetica", "B", 15)
        self.cell(80)
        self.set_text_color(44, 62, 80)  # Dark Blue
        self.cell(30, 10, "BankTamer Financial Report", border=0, align="C", new_x="RIGHT", new_y="TOP")
        self.ln(30)

    def footer(self) -> None:
        """Render the PDF footer with page numbers."""
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(127, 140, 141)  # Grey
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", border=0, align="C", new_x="RIGHT", new_y="TOP")

    def draw_card(
        self, title: str, value: float, color: tuple[int, int, int], x: float, y: float, w: float, h: float
    ) -> None:
        """Draw a metric card with a title and value."""
        self.set_fill_color(248, 249, 250)
        self.set_draw_color(222, 226, 230)
        self.rect(x, y, w, h, "DF")

        self.set_xy(x, y + 2)
        self.set_font("helvetica", "", 10)
        self.set_text_color(108, 117, 125)
        self.cell(w, 5, title, border=0, align="C", new_x="RIGHT", new_y="TOP")

        self.set_xy(x, y + 8)
        self.set_font("helvetica", "B", 14)
        self.set_text_color(*color)
        self.cell(w, 8, f"{value:,.2f}", border=0, align="C", new_x="RIGHT", new_y="TOP")

    def render(self, report_data: dict[str, MonthReport], output_path: str = "banktamer_report.pdf") -> None:
        """Render all monthly reports into a single PDF file."""
        self.set_auto_page_break(auto=True, margin=15)
        self.alias_nb_pages()

        # Color palette
        green = (40, 167, 69)
        red = (220, 53, 69)
        dark = (33, 37, 41)
        expense_colors = [
            (220, 53, 69),  # Red
            (0, 123, 255),  # Blue
            (255, 193, 7),  # Yellow
            (111, 66, 193),  # Purple
            (23, 162, 184),  # Cyan
            (253, 126, 20),  # Orange
        ]

        for month, data in sorted(report_data.items()):
            self.add_page()

            # Month Title
            self.set_font("helvetica", "B", 20)
            self.set_text_color(*dark)
            self.cell(0, 15, f"Summary: {month}", border=0, align="L", new_x="LMARGIN", new_y="NEXT")
            self.ln(5)

            # Summary Cards
            y_start = self.get_y()
            card_w = (self.w - 30) / 3
            self.draw_card("Total Income", data["total_income"], green, 10, y_start, card_w, 20)
            self.draw_card("Total Expenses", data["total_expenses"], red, 10 + card_w + 5, y_start, card_w, 20)

            balance = data["total_income"] + data["total_expenses"]
            balance_color = green if balance >= 0 else red
            self.draw_card("Net Balance", balance, balance_color, 10 + (card_w + 5) * 2, y_start, card_w, 20)

            self.set_y(y_start + 25)
            self.ln(10)

            # Categorized Breakdown Table
            self.set_font("helvetica", "B", 14)
            self.set_text_color(*dark)
            self.cell(0, 10, "Categorized Breakdown", border=0, align="L", new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

            # Table Header
            self.set_fill_color(240, 240, 240)
            self.set_font("helvetica", "B", 10)
            self.set_text_color(*dark)
            col_widths = [45, 25, 20, 100]
            headers = ["Category", "Total", "%", "Max Transaction"]
            for w, h_text in zip(col_widths, headers):
                self.cell(w, 8, h_text, border=1, align="C", new_x="RIGHT", new_y="TOP", fill=True)
            self.ln()

            # Filter categories with non-zero absolute total for sorting/charts
            categories_to_plot = {cat: stats for cat, stats in data["categories"].items() if abs(stats.total) > 0}
            sorted_categories = sorted(categories_to_plot.items(), key=lambda x: abs(x[1].total), reverse=True)

            self.set_font("helvetica", "", 9)
            category_colors: dict[str, tuple[int, int, int]] = {}
            expense_color_idx = 0

            for cat, stats in sorted_categories:
                if stats.total > 0:
                    color = green
                    total_for_percent = data["total_income"]
                else:
                    color = expense_colors[expense_color_idx % len(expense_colors)]
                    expense_color_idx += 1
                    total_for_percent = abs(data["total_expenses"])

                percent = (abs(stats.total) / total_for_percent * 100) if total_for_percent != 0 else 0.0
                category_colors[cat] = color

                # Row Data
                self.set_text_color(*dark)
                self.cell(col_widths[0], 8, cat, border=1, align="L", new_x="RIGHT", new_y="TOP")

                self.set_text_color(*color)
                self.cell(col_widths[1], 8, f"{stats.total:,.2f}", border=1, align="R", new_x="RIGHT", new_y="TOP")

                self.set_text_color(*dark)
                self.cell(col_widths[2], 8, f"{percent:.1f}%", border=1, align="R", new_x="RIGHT", new_y="TOP")

                max_txn_txt = ""
                if stats.max_txn:
                    amount_txt = f"{stats.max_txn.amount:,.2f}"
                    concept_txt = (
                        f"{stats.max_txn.concept[:45]}..."
                        if len(stats.max_txn.concept) > 45
                        else stats.max_txn.concept
                    )
                    max_txn_txt = f"{amount_txt} ({concept_txt})"
                self.cell(col_widths[3], 8, max_txn_txt, border=1, align="L", new_x="LMARGIN", new_y="NEXT")

            self.ln(10)

            # Proportional Distribution
            if sorted_categories:
                self.ln(5)
                self.set_font("helvetica", "B", 12)
                self.set_text_color(*dark)
                self.cell(
                    0, 10, "Financial Distribution (Proportions)", border=0, align="L", new_x="LMARGIN", new_y="NEXT"
                )

                total_abs = sum(abs(s.total) for _, s in sorted_categories)

                for cat, stats in sorted_categories:
                    val = abs(stats.total)
                    if total_abs == 0:
                        continue
                    percent = (val / total_abs) * 100

                    color = category_colors[cat]

                    # Bar
                    self.set_font("helvetica", "", 9)
                    self.set_text_color(*dark)
                    self.cell(40, 6, cat, border=0, align="L", new_x="RIGHT", new_y="TOP")

                    bar_max_w = 120
                    bar_w = (percent / 100) * bar_max_w

                    curr_x, curr_y = self.get_x(), self.get_y()
                    self.set_fill_color(*color)
                    self.rect(curr_x, curr_y + 1, bar_w, 4, "F")

                    self.set_xy(curr_x + bar_max_w + 5, curr_y)
                    self.cell(20, 6, f"{percent:.1f}%", border=0, align="L", new_x="LMARGIN", new_y="NEXT")

            # Unknown Concepts
            if data["unknown_concepts"]:
                self.ln(5)
                self.set_font("helvetica", "B", 12)
                self.set_text_color(*red)
                self.cell(0, 10, "Unknown Expense Concepts", border=0, align="L", new_x="LMARGIN", new_y="NEXT")
                self.set_font("helvetica", "", 9)
                self.set_text_color(*dark)
                for dt, amt, concept in sorted(data["unknown_concepts"], key=lambda x: x[0]):
                    self.cell(0, 5, f"{dt} | {amt:,.2f} | {concept}", border=0, align="L", new_x="LMARGIN", new_y="NEXT")

        self.output(output_path)
