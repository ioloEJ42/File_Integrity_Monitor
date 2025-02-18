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
        alerts = monitor.db.get_all_alerts()  # Ensure alerts are available

        if not alerts:
            console.print("[red]No alerts to export.[/red]")
            return False

        # Metadata
        pdf_metadata = {
            "Title": "File Integrity Monitor Report",
            "Author": "IEJ File Monitor",
            "Subject": "File System Changes Report",
            "CreationDate": datetime.now(),
        }

        # File Path Setup
        if not export_path:
            export_path = get_export_path("pdf")

        doc = SimpleDocTemplate(export_path, pagesize=landscape(letter))

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

        # Summary Statistics
        event_counts = defaultdict(int)
        for alert in alerts:
            event_counts[alert[2]] += 1  # Count occurrences of event types

        most_common_event = (
            max(event_counts, key=event_counts.get) if event_counts else "N/A"
        )
        created_count = event_counts.get("CREATED", 0)
        modified_count = event_counts.get("MODIFIED", 0)
        deleted_count = event_counts.get("DELETED", 0)

        summary_data = [
            ["Total Events", str(len(alerts))],
            ["Monitoring Period", f"{alerts[0][0]} to {alerts[-1][0]}"],
            ["Most Common Event", most_common_event],
            ["Modified Files", str(modified_count)],
            ["Created Files", str(created_count)],
            ["Deleted Files", str(deleted_count)],
        ]

        summary_table = Table(summary_data, colWidths=[2 * inch, 4 * inch])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F5F5F5")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2C3E50")),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#E0E0E0")),
                ]
            )
        )

        # Pie Chart: Event Distribution
        def create_event_chart(alerts):
            drawing = Drawing(400, 200)
            pie = Pie()
            pie.x = 100
            pie.y = 25
            pie.width = 200
            pie.height = 150

            pie.data = list(event_counts.values())
            pie.labels = list(event_counts.keys())
            pie.slices.strokeWidth = 0.5
            pie.slices[0].fillColor = colors.green
            pie.slices[1].fillColor = colors.blue
            pie.slices[2].fillColor = colors.red

            drawing.add(pie)
            return drawing

        # Bar Chart: Hourly Event Analysis
        def analyze_time_patterns(alerts):
            hourly_distribution = defaultdict(int)
            for alert in alerts:
                timestamp = datetime.fromisoformat(alert[0])
                hourly_distribution[timestamp.hour] += 1

            drawing = Drawing(400, 200)
            bar_chart = VerticalBarChart()
            bar_chart.x = 50
            bar_chart.y = 50
            bar_chart.height = 125
            bar_chart.width = 300
            bar_chart.data = [list(hourly_distribution.values())]
            bar_chart.categoryAxis.categoryNames = [
                str(h) for h in hourly_distribution.keys()
            ]
            bar_chart.barWidth = 8

            drawing.add(bar_chart)
            return drawing

        # Page Numbering
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

        # Build PDF
        elements = []

        # Title
        elements.append(Paragraph("File Integrity Monitor Report", styles["Title"]))
        elements.append(Spacer(1, 12))

        # Summary Table
        elements.append(Paragraph("Summary Statistics", styles["SectionHeader"]))
        elements.append(summary_table)
        elements.append(Spacer(1, 24))

        # Pie Chart
        elements.append(Paragraph("Event Type Distribution", styles["SectionHeader"]))
        elements.append(create_event_chart(alerts))
        elements.append(Spacer(1, 24))

        # Bar Chart
        elements.append(Paragraph("File Events by Hour", styles["SectionHeader"]))
        elements.append(analyze_time_patterns(alerts))
        elements.append(Spacer(1, 24))

        # Table of Events
        elements.append(Paragraph("Detailed File Events", styles["SectionHeader"]))

        data = [["Timestamp", "File Path", "Event Type", "Details"]]
        for alert in alerts:
            data.append([alert[0], alert[1], alert[2], alert[3]])

        event_table = Table(
            data, colWidths=[1.5 * inch, 4 * inch, 1.5 * inch, 3 * inch]
        )
        event_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
        elements.append(event_table)

        # Generate PDF
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
