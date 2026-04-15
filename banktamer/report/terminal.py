import math
from typing import TypedDict
from banktamer.analytics import MonthReport, CategoryStats


class SliceInfo(TypedDict):
    """Structure for pie chart slice information."""

    start: float
    end: float
    color: str


def print_report(report_data: dict[str, MonthReport]) -> None:
    """Print a rich terminal report including charts and summaries."""
    # Color constants
    green = "\033[92m"
    red = "\033[91m"
    blue = "\033[94m"
    yellow = "\033[93m"
    magenta = "\033[95m"
    cyan = "\033[96m"
    white = "\033[97m"
    reset = "\033[0m"
    bold = "\033[1m"

    palette_expenses = [red, blue, yellow, magenta, cyan, white]

    # Pre-assign consistent colors to all categories across all months
    all_categories: set[str] = set()
    income_categories: set[str] = set()
    for month_data in report_data.values():
        for cat, stats in month_data["categories"].items():
            all_categories.add(cat)
            if stats.total > 0:
                income_categories.add(cat)

    all_category_colors: dict[str, str] = {}
    expense_color_idx = 0
    for cat in sorted(all_categories):
        if cat in income_categories:
            all_category_colors[cat] = green
        else:
            all_category_colors[cat] = palette_expenses[expense_color_idx % len(palette_expenses)]
            expense_color_idx += 1

    for month, data in report_data.items():
        print(f"\n{blue}{'=' * 50}{reset}")
        print(f" {bold}REPORT FOR {month}{reset}")
        print(f"{blue}{'=' * 50}{reset}")

        # Filter categories with non-zero absolute total for sorting/charts
        categories_to_plot = {cat: stats for cat, stats in data["categories"].items() if abs(stats.total) > 0}

        # Sort categories by total absolute amount
        sorted_categories = sorted(categories_to_plot.items(), key=lambda x: abs(x[1].total), reverse=True)

        print("\nCATEGORIZED BREAKDOWN:")
        print(f"{'Category':<20} | {'Total':>10} | {'%':>6} | {'Max Transaction'}")
        print("-" * 85)

        category_colors: dict[str, str] = {}
        for cat, stats in sorted_categories:
            color = all_category_colors[cat]
            if stats.total > 0:
                total_for_percent = data["total_income"]
            else:
                total_for_percent = data["total_expenses"]

            percentage = (stats.total / total_for_percent * 100) if total_for_percent != 0 else 0.0
            category_colors[cat] = color

            max_txn_str = ""
            if stats.max_txn:
                max_txn_str = f"{stats.max_txn.amount:>10.2f} ({stats.max_txn.concept})"

            line = f"{cat:<20} | {color}{stats.total:>10.2f}{reset} | {percentage:>5.1f}% | {max_txn_str}"
            print(line)

            if abs(percentage) > 0:
                bar_width = 30
                filled_width = int((abs(percentage) / 100) * bar_width)
                bar = "█" * filled_width
                print(f"{' ': <23} {color}{bar}{reset}")

        print("\nMONTHLY SUMMARY:")
        print(f"Total Income:   {green}{data['total_income']:>10.2f}{reset}")
        print(f"Total Expenses: {red}{data['total_expenses']:>10.2f}{reset}")
        balance = data["total_income"] + data["total_expenses"]
        balance_color = green if balance >= 0 else red
        print(f"Net Balance:    {balance_color}{balance:>10.2f}{reset}")

        if data["unknown_concepts"]:
            print(f"\n{bold}UNKNOWN EXPENSE CONCEPTS:{reset}")
            for date_val, amount, concept in sorted(data["unknown_concepts"], key=lambda x: x[0]):
                print(f"- {date_val} | {red}{amount:>10.2f}{reset} | {concept}")

        if sorted_categories:
            render_pie_chart(sorted_categories, category_colors)

    # Evolution Chart
    if report_data:
        from banktamer.analytics import AnalyticsProcessor

        processor = AnalyticsProcessor()
        months, evolution = processor.get_evolution_data(report_data)
        render_evolution_chart(months, evolution, all_category_colors)


def render_pie_chart(sorted_categories: list[tuple[str, CategoryStats]], category_colors: dict[str, str]) -> None:
    """Render a text-based pie chart in the terminal."""
    # Include all categories (both income and expenses) in a single pie chart
    plot_data = []
    total_abs = 0.0

    for cat, stats in sorted_categories:
        plot_data.append((cat, abs(stats.total)))
        total_abs += abs(stats.total)

    if total_abs == 0:
        return

    # Dimensions
    # Chars are taller than wide, so we compensate with width
    height = 10
    width = 20

    # Pre-calculate slice boundaries in radians
    slices: list[SliceInfo] = []
    current_angle = 0.0
    for i, (cat, val) in enumerate(plot_data):
        slice_angle = (val / total_abs) * 2 * math.pi
        slices.append({"start": current_angle, "end": current_angle + slice_angle, "color": category_colors[cat]})
        current_angle += slice_angle

    # Draw grid
    print("\nFINANCIAL DISTRIBUTION:")
    for y in range(height):
        line = " " * 10  # indent
        for x in range(width):
            # Normalize to -1 to 1
            nx = (x / (width - 1)) * 2 - 1
            ny = (y / (height - 1)) * 2 - 1

            # Distance from center
            dist = nx * nx + ny * ny
            if dist <= 1.0:
                # Calculate angle
                angle = math.atan2(ny, nx)  # -pi to pi
                if angle < 0:
                    angle += 2 * math.pi

                char_color = "\033[90m"  # default gray
                for slice_info in slices:
                    if slice_info["start"] <= angle < slice_info["end"]:
                        char_color = slice_info["color"]
                        break
                line += f"{char_color}█\033[0m"
            else:
                line += " "
        print(line)


def render_evolution_chart(months: list[str], evolution: dict[str, list[float]], cat_colors: dict[str, str]) -> None:
    """Render a text-based line chart in the terminal."""
    if not months or not evolution:
        return

    print(f"\n\033[94m{'=' * 50}\033[0m")
    print(" \033[1mEVOLUTION OF INCOMES/EXPENSES\033[0m")
    print(f"\033[94m{'=' * 50}\033[0m")

    # Dimensions
    height = 15
    width_per_month = 10
    total_width = len(months) * width_per_month

    # Get max/min values for scaling
    all_vals = [v for vals in evolution.values() for v in vals]
    max_val = max(all_vals) if all_vals else 1.0
    min_val = min(all_vals) if all_vals else 0.0

    # Ensure range is at least something
    if max_val == min_val:
        max_val += 1.0

    # Create grid (list of lists of color/char)
    grid = [[(" ", "\033[0m") for _ in range(total_width)] for _ in range(height)]

    # Draw categories
    for cat, vals in evolution.items():
        color = cat_colors.get(cat, "\033[97m")
        points = []
        for i, val in enumerate(vals):
            # Scale x
            x = i * width_per_month + width_per_month // 2
            # Scale y (inverted for terminal)
            y_norm = (val - min_val) / (max_val - min_val)
            y = height - 1 - int(y_norm * (height - 1))
            points.append((x, y))

        # Draw dots
        for px, py in points:
            if 0 <= px < total_width and 0 <= py < height:
                grid[py][px] = ("●", color)

        # Draw simple horizontal lines between points
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            # Just fill characters between them (very basic line drawing)
            num_steps = max(abs(x2 - x1), abs(y2 - y1))
            for step in range(1, num_steps):
                curr_x = x1 + int(step * (x2 - x1) / num_steps)
                curr_y = y1 + int(step * (y2 - y1) / num_steps)
                if 0 <= curr_x < total_width and 0 <= curr_y < height:
                    # Don't overwrite dots
                    if grid[curr_y][curr_x][0] == " ":
                        grid[curr_y][curr_x] = ("·", color)

    # Print grid with Y axis
    for y in range(height):
        # Y axis label
        val = max_val - (y / (height - 1)) * (max_val - min_val)
        label = f"{val:>8.0f} |"
        line = label
        for x in range(total_width):
            char, color = grid[y][x]
            line += f"{color}{char}\033[0m"
        print(line)

    # X axis
    print(f"{' ' * 9}{'-' * total_width}")
    # X axis labels
    x_labels = " " * 9
    for month in months:
        # Center the label
        label = month.center(width_per_month)
        x_labels += label
    print(x_labels)

    # Legend
    print("\nLEGEND:")
    categories = sorted(evolution.keys())
    for i in range(0, len(categories), 3):
        chunk = categories[i : i + 3]
        line = "  "
        for cat in chunk:
            color = cat_colors.get(cat, "\033[0m")
            line += f"{color}● {cat:<20}\033[0m"
        print(line)


def print_ai_analysis(provider_name: str, content: str) -> None:
    """Print the AI analysis with a header and styling."""
    blue = "\033[94m"
    bold = "\033[1m"
    reset = "\033[0m"

    print(f"\n{blue}{'=' * 50}{reset}")
    print(f" {bold}AI FINANCIAL ANALYSIS ({provider_name.upper()}){reset}")
    print(f"{blue}{'=' * 50}{reset}")
    print(content)
    print(f"{blue}{'=' * 50}{reset}")
