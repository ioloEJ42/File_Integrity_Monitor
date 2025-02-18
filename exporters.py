# exporters.py

import os
import csv
from datetime import datetime
from rich.console import Console
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.textlabels import Label
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.graphics import renderPDF
from collections import defaultdict
from reportlab.pdfgen import canvas
from textwrap import wrap

console = Console()


def get_export_path(extension, base_dir=None):
    """Generate export path with timestamp"""
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    exports_dir = os.path.join(base_dir, "exports")
    os.makedirs(exports_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(exports_dir, f"fim_logs_{timestamp}.{extension}")


def export_to_csv(monitor, export_path=None):
    try:
        if not export_path:
            export_path = get_export_path("csv")

        alerts = monitor.db.get_all_alerts()

        with open(export_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Timestamp", "File Path", "Event Type", "Details"])
            writer.writerows(alerts)

        console.print(f"[green]Logs exported successfully to: {export_path}[/green]")
        return True
    except Exception as e:
        console.print(f"[red]Error exporting logs: {str(e)}[/red]")
        return False


def export_to_pdf(monitor, export_path=None):
    """Export alerts to a detailed PDF report with summary statistics and visualizations."""
    try:
        alerts = monitor.db.get_all_alerts()
        if not alerts:
            console.print("[red]No alerts to export.[/red]")
            return False

        # Enhanced metadata
        pdf_metadata = {
            "Title": "File Integrity Monitor Report",
            "Author": "IEJ File Monitor",
            "Subject": "File System Changes Report",
            "CreationDate": datetime.now(),
        }

        if not export_path:
            export_path = get_export_path("pdf")

        # Create document with better margins
        doc = SimpleDocTemplate(
            export_path,
            pagesize=landscape(letter),
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50,
        )

        # Styles
        styles = getSampleStyleSheet()
        styles.add(
            ParagraphStyle(
                "SectionHeader",
                parent=styles["Heading2"],
                fontSize=14,
                spaceAfter=10,
                textColor=colors.HexColor("#2C3E50"),
            )
        )

        styles.add(
            ParagraphStyle(
                "MainTitle",
                parent=styles["Title"],
                fontSize=24,
                spaceAfter=30,
                textColor=colors.HexColor("#2C3E50"),
                alignment=1,
            )
        )

        styles.add(
            ParagraphStyle(
                "SubTitle",
                parent=styles["Heading2"],
                fontSize=16,
                spaceBefore=20,
                spaceAfter=20,
                textColor=colors.HexColor("#34495E"),
                alignment=1,
            )
        )

        styles.add(
            ParagraphStyle(
                "TimeStamp",
                parent=styles["Normal"],
                fontSize=10,
                textColor=colors.HexColor("#7F8C8D"),
                alignment=1,
            )
        )

        class NumberedCanvas(canvas.Canvas):
            def __init__(self, *args, **kwargs):
                canvas.Canvas.__init__(self, *args, **kwargs)
                self._saved_page_states = []

            def showPage(self):
                self._saved_page_states.append(dict(self.__dict__))
                self._startPage()

            def save(self):
                num_pages = len(self._saved_page_states)
                for state in self._saved_page_states:
                    self.__dict__.update(state)
                    self.draw_page_number(num_pages)
                    canvas.Canvas.showPage(self)
                canvas.Canvas.save(self)

            def draw_page_number(self, page_count):
                self.setFont("Helvetica", 9)
                self.drawRightString(
                    self._pagesize[0] - 36,
                    36,
                    f"Page {self._pageNumber} of {page_count}",
                )

        elements = []

        # Title Block
        elements.append(Paragraph("File Integrity Monitor Report", styles["MainTitle"]))
        elements.append(
            Paragraph(
                f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                styles["TimeStamp"],
            )
        )
        elements.append(Spacer(1, 30))

        # Summary Statistics
        event_counts = defaultdict(int)
        for alert in alerts:
            event_counts[alert[2]] += 1

        summary_data = [
            ["Monitoring Period", f"{alerts[0][0]} to {alerts[-1][0]}"],
            ["Total Events", str(len(alerts))],
            ["Created Files", str(event_counts.get("CREATED", 0))],
            ["Modified Files", str(event_counts.get("MODIFIED", 0))],
            ["Deleted Files", str(event_counts.get("DELETED", 0))],
            ["Renamed Files", str(event_counts.get("RENAMED", 0))],
        ]

        # Enhanced Summary Table
        summary_table = Table(summary_data, colWidths=[2.5 * inch, 5 * inch])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8F9FA")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2C3E50")),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 12),
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#E9ECEF")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 0),
                        (-1, -1),
                        [colors.HexColor("#FFFFFF"), colors.HexColor("#F8F9FA")],
                    ),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ]
            )
        )

        elements.append(Paragraph("Summary Statistics", styles["SubTitle"]))
        elements.append(summary_table)
        elements.append(PageBreak())

        # Create charts
        def create_event_chart(alerts):
            drawing = Drawing(400, 200)
            pie = Pie()
            pie.x = 100
            pie.y = 25
            pie.width = 200
            pie.height = 150

            # Get data and calculate percentages
            total_events = sum(event_counts.values())
            formatted_labels = []
            for event_type, count in zip(event_counts.keys(), event_counts.values()):
                percentage = (count / total_events) * 100
                formatted_labels.append(f"{event_type} ({count}, {percentage:.1f}%)")

            pie.data = list(event_counts.values())
            pie.labels = formatted_labels
            pie.slices.strokeWidth = 0.5

            # Set colors for each type
            for i, (event_type, _) in enumerate(event_counts.items()):
                if event_type == "CREATED":
                    pie.slices[i].fillColor = colors.green
                elif event_type == "MODIFIED":
                    pie.slices[i].fillColor = colors.red
                elif event_type == "DELETED":
                    pie.slices[i].fillColor = colors.blue
                else:  # RENAMED
                    pie.slices[i].fillColor = colors.cyan

            drawing.add(pie)
            return drawing

        def analyze_time_patterns(alerts):
            # First, calculate the total time span
            timestamps = [datetime.fromisoformat(alert[0]) for alert in alerts]
            time_span = max(timestamps) - min(timestamps)
            total_minutes = time_span.total_seconds() / 60

            drawing = Drawing(400, 200)
            bar_chart = VerticalBarChart()

            # If monitoring period is less than 1 hour, use minute-based intervals
            if total_minutes < 60:
                distribution = defaultdict(int)
                for timestamp in timestamps:
                    minute = timestamp.minute
                    distribution[minute] += 1

                bar_chart.data = [list(distribution.values())]
                bar_chart.categoryAxis.categoryNames = [
                    f"Min {m}" for m in distribution.keys()
                ]
                y_label = "Events per Minute"
            else:
                # Use original hourly distribution
                hourly_distribution = defaultdict(int)
                for timestamp in timestamps:
                    hour = timestamp.hour
                    hourly_distribution[hour] += 1

                bar_chart.data = [list(hourly_distribution.values())]
                bar_chart.categoryAxis.categoryNames = [
                    f"Hour {h}" for h in hourly_distribution.keys()
                ]
                y_label = "Events per Hour"

            # Improved bar chart styling
            bar_chart.x = 50
            bar_chart.y = 50
            bar_chart.height = 125
            bar_chart.width = 300
            bar_chart.barWidth = 8

            # Add proper styling
            bar_chart.valueAxis.labels.fontSize = 8
            bar_chart.categoryAxis.labels.fontSize = 8
            bar_chart.valueAxis.strokeWidth = 0.5
            bar_chart.valueAxis.strokeColor = colors.grey
            bar_chart.bars[0].fillColor = colors.HexColor("#2C3E50")

            drawing.add(bar_chart)
            return drawing

        # Create and add charts side by side
        pie_chart = create_event_chart(alerts)
        bar_chart = analyze_time_patterns(alerts)

        chart_table = Table(
            [[pie_chart, bar_chart]], colWidths=[4.5 * inch, 4.5 * inch]
        )
        chart_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        elements.append(Paragraph("Event Analysis", styles["SubTitle"]))
        elements.append(chart_table)
        elements.append(PageBreak())

        # Detailed Events Table
        elements.append(Paragraph("Detailed File Events", styles["SectionHeader"]))

        # Format the data with better timestamp and path handling
        data = [
            ["Timestamp", "File Path", "Event Type", "Details (User, SHA-256 hash)"]
        ]
        for alert in alerts:
            timestamp = datetime.fromisoformat(alert[0]).strftime("%Y-%m-%d %H:%M:%S")
            file_path = os.path.basename(alert[1])  # Show only filename
            formatted_details = (
                f"User: {alert[3].split('User: ')[1].split(',')[0]}<br/>"
            )
            if "Hash changed" in alert[3]:
                hash_data = alert[3].split("Hash changed: ")[1].split("->")
                old_hash = (
                    "None"
                    if "None" in hash_data[0]
                    else "<br/>".join(wrap(hash_data[0], 32))
                )
                new_hash = "<br/>".join(wrap(hash_data[1], 32))
                formatted_details += f"Hash changed:<br/>{old_hash} -><br/>{new_hash}"

            data.append(
                [
                    timestamp,
                    Paragraph(file_path, styles["Normal"]),
                    alert[2],
                    Paragraph(formatted_details, styles["Normal"]),
                ]
            )

        event_table = Table(
            data, colWidths=[1.2 * inch, 2.5 * inch, 1.2 * inch, None], repeatRows=1
        )

        event_table.setStyle(
            TableStyle(
                [
                    # Header
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    # Alternating rows
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.HexColor("#FFFFFF"), colors.HexColor("#F8F9FA")],
                    ),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E9ECEF")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("TOPPADDING", (0, 0), (-1, 0), 12),
                ]
            )
        )

        elements.append(event_table)

        # Generate PDF with page numbers
        doc.build(elements, canvasmaker=NumberedCanvas)
        console.print(f"[green]Logs exported successfully to: {export_path}[/green]")
        return True

    except Exception as e:
        console.print(f"[red]Error exporting logs to PDF: {str(e)}[/red]")
        return False


def export_logs(monitor):
    """Handle log export to either CSV or PDF"""
    try:
        format_choice = input("Export format (csv/pdf): ").lower().strip()
        if format_choice in ["csv", "pdf"]:
            if format_choice == "csv":
                return export_to_csv(monitor)
            else:
                return export_to_pdf(monitor)
        else:
            console.print(
                "[red]Invalid format choice. Please choose 'csv' or 'pdf'[/red]"
            )
            return False
    except Exception as e:
        console.print(f"[red]Error during export: {str(e)}[/red]")
        return False
