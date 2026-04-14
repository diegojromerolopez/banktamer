import math
from banktamer.analytics import MonthReport


def print_report(report_data: dict[str, MonthReport]) -> None:
    # Color constants
    GREEN = "\033[92m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    PALETTE_EXPENSES = [RED, BLUE, YELLOW, MAGENTA, CYAN, WHITE]

    for month, data in report_data.items():
        print(f"\n{BLUE}{'=' * 50}{RESET}")
        print(f" {BOLD}REPORT FOR {month}{RESET}")
        print(f"{BLUE}{'=' * 50}{RESET}")

        # Filter categories with non-zero absolute total for sorting/charts
        categories_to_plot = {cat: stats for cat, stats in data["categories"].items() if abs(stats.total) > 0}
        
        # Sort categories by total absolute amount
        sorted_categories = sorted(categories_to_plot.items(), key=lambda x: abs(x[1].total), reverse=True)

        print("\nCATEGORIZED BREAKDOWN:")
        print(f"{'Category':<20} | {'Total':>10} | {'%':>6} | {'Max Transaction'}")
        print("-" * 85)

        category_colors: dict[str, str] = {}
        expense_color_idx = 0

        for cat, stats in sorted_categories:
            percentage = 0.0
            if stats.total > 0:
                color = GREEN
                if data["total_income"] > 0:
                    percentage = (stats.total / data["total_income"]) * 100
            else:
                color = PALETTE_EXPENSES[expense_color_idx % len(PALETTE_EXPENSES)]
                expense_color_idx += 1
                if data["total_expenses"] < 0:
                    percentage = (stats.total / data["total_expenses"]) * 100
            
            category_colors[cat] = color

            max_txn_str = ""
            if stats.max_txn:
                max_txn_str = f"{stats.max_txn.amount:>10.2f} ({stats.max_txn.concept})"

            line = f"{cat:<20} | {color}{stats.total:>10.2f}{RESET} | {percentage:>5.1f}% | {max_txn_str}"
            print(line)

            if abs(percentage) > 0:
                bar_width = 30
                filled_width = int((percentage / 100) * bar_width)
                bar = "█" * filled_width
                print(f"{' ': <23} {color}{bar}{RESET}")

        print("\nMONTHLY SUMMARY:")
        print(f"Total Income:   {GREEN}{data['total_income']:>10.2f}{RESET}")
        print(f"Total Expenses: {RED}{data['total_expenses']:>10.2f}{RESET}")
        balance = data["total_income"] + data["total_expenses"]
        balance_color = GREEN if balance >= 0 else RED
        print(f"Net Balance:    {balance_color}{balance:>10.2f}{RESET}")

        if data["unknown_concepts"]:
            print(f"\n{BOLD}UNKNOWN EXPENSE CONCEPTS:{RESET}")
            for date_val, amount, concept in sorted(data["unknown_concepts"], key=lambda x: x[0]):
                print(f"- {date_val} | {RED}{amount:>10.2f}{RESET} | {concept}")

        if sorted_categories:
            render_pie_chart(sorted_categories, category_colors)


def render_pie_chart(
    sorted_categories: list[tuple[str, any]], category_colors: dict[str, str]
) -> None:
    # Include all categories (both income and expenses) in a single pie chart
    plot_data = []
    total_abs = 0.0
    
    for cat, stats in sorted_categories:
        plot_data.append((cat, abs(stats.total)))
        total_abs += abs(stats.total)

    if total_abs == 0:
        return

    # Dimensions
    height = 10
    width = 20 # chars are taller than wide
    
    # Pre-calculate slice boundaries in radians
    slices = []
    current_angle = 0.0
    for i, (cat, val) in enumerate(plot_data):
        slice_angle = (val / total_abs) * 2 * math.pi
        slices.append({"start": current_angle, "end": current_angle + slice_angle, "color": category_colors[cat]})
        current_angle += slice_angle

    # Draw grid
    print("\nFINANCIAL DISTRIBUTION:")
    for y in range(height):
        line = " " * 10 # indent
        for x in range(width):
            # Normalize to -1 to 1
            nx = (x / (width - 1)) * 2 - 1
            ny = (y / (height - 1)) * 2 - 1
            
            # Distance from center
            dist = nx*nx + ny*ny
            if dist <= 1.0:
                # Calculate angle
                angle = math.atan2(ny, nx) # -pi to pi
                if angle < 0:
                    angle += 2 * math.pi
                
                char_color = "\033[90m" # default gray
                for slice_info in slices:
                    if slice_info["start"] <= angle < slice_info["end"]:
                        char_color = slice_info["color"]
                        break
                line += f"{char_color}█\033[0m"
            else:
                line += " "
        print(line)
