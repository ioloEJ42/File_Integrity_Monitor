# IEJ$$$$$\$$$$$$\ $$\      $$\
# $$  _____\_$$  _|$$$\    $$$ |
# $$ |       $$ |  $$$$\  $$$$ |
# $$$$$\     $$ |  $$\$$\$$ $$ |
# $$  __|    $$ |  $$ \$$$  $$ |
# $$ |       $$ |  $$ |\$  /$$ |
# $$ |     $$$$$$\ $$ | \_/ $$ |
# \__|     \______|\__|     \__|

# Made by IEJ

import os
import hashlib
import sqlite3
import time
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from rich.console import Console
import platform

# Pdf Exporting Imports
from exporters import export_to_csv, export_to_pdf, export_logs

console = Console()


def get_key():
    """Get a single keypress from the user"""
    if platform.system() == "Windows":
        import msvcrt

        return msvcrt.getch().decode("utf-8").lower()
    else:
        import sys
        import tty
        import termios

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1).lower()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


def clean_path(path):
    # Strip quotes and whitespace
    path = path.strip().strip('"').strip("'").strip()

    if os.name == "nt":  # Windows
        # Normalize slashes to Windows style and resolve any relative components
        path = os.path.normpath(path.replace("/", "\\"))
        # Ensure proper absolute path
        return os.path.abspath(path)
    else:  # Unix/WSL
        # Check if this is a Windows path (e.g., C:\, D:\, etc.)
        if len(path) > 1 and path[0].isalpha() and path[1] == ":":
            # Convert Windows path to WSL
            drive_letter = path[0].lower()
            # Remove drive letter and colon, normalize slashes
            win_path = path[2:].replace("\\", "/").lstrip("/")
            path = f"/mnt/{drive_letter}/{win_path}"

        # Normalize the path for Unix systems
        return os.path.abspath(path)


class Database:
    def __init__(self, db_file="file_hashes.db"):
        self.db_file = db_file
        self.init_database()

    def init_database(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS file_hashes (
                    file_path TEXT PRIMARY KEY,
                    hash TEXT,
                    last_modified TEXT,
                    permissions TEXT
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    timestamp TEXT,
                    file_path TEXT,
                    event_type TEXT,
                    details TEXT
                )
            """
            )

    def get_all_alerts(self):
        """Retrieve all alerts from the database"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT timestamp, file_path, event_type, details FROM alerts ORDER BY timestamp"
            )
            return cursor.fetchall()

    def store_file_hash(self, file_path, file_hash, last_modified, permissions):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO file_hashes 
                (file_path, hash, last_modified, permissions) 
                VALUES (?, ?, ?, ?)
            """,
                (file_path, file_hash, last_modified, permissions),
            )

    def get_file_hash(self, file_path):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT hash FROM file_hashes WHERE file_path = ?", (file_path,)
            )
            result = cursor.fetchone()
            return result[0] if result else None

    def log_alert(self, file_path, event_type, details):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            timestamp = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO alerts (timestamp, file_path, event_type, details)
                VALUES (?, ?, ?, ?)
            """,
                (timestamp, file_path, event_type, details),
            )


class FileMonitor:
    def __init__(self, path_to_monitor):
        self.path_to_monitor = path_to_monitor
        self.db = Database()
        self.baseline_hashes = {}

    def calculate_file_hash(self, file_path):
        """Calculate SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            console.print(f"[red]Error calculating hash for {file_path}: {e}[/red]")
            return None

    def establish_baseline(self):
        """Create initial baseline of files and their hashes."""
        console.print("[yellow]Establishing baseline...[/yellow]")
        for root, _, files in os.walk(self.path_to_monitor):
            for file in files:
                file_path = os.path.join(root, file)
                file_hash = self.calculate_file_hash(file_path)
                if file_hash:
                    stats = os.stat(file_path)
                    self.db.store_file_hash(
                        file_path,
                        file_hash,
                        datetime.fromtimestamp(stats.st_mtime).isoformat(),
                        str(oct(stats.st_mode)[-3:]),
                    )
        console.print("[green]Baseline established![/green]")


class FileEventHandler(FileSystemEventHandler):
    def __init__(self, monitor):
        self.monitor = monitor
        super().__init__()

    def format_path(self, path):
        """Format path string to remove any line breaks"""
        return path.replace("\n", "").replace("\r", "").strip()

    def on_modified(self, event):
        if not event.is_directory:
            self._handle_file_event(event.src_path, "MODIFIED")

    def on_created(self, event):
        if not event.is_directory:
            self._handle_file_event(event.src_path, "CREATED")

    def on_deleted(self, event):
        if not event.is_directory:
            self._handle_file_event(event.src_path, "DELETED")

    def on_moved(self, event):
        if not event.is_directory:
            self._handle_rename_event(event.src_path, event.dest_path)

    def _handle_rename_event(self, src_path, dest_path):
        src_path_clean = self.format_path(src_path)
        dest_path_clean = self.format_path(dest_path)
        alert_msg = f"File RENAMED: {src_path_clean} -> {dest_path_clean}"
        console.print(f"[yellow]{alert_msg}[/yellow]")
        self.monitor.db.log_alert(dest_path, "RENAMED", f"Renamed from: {src_path}")

        # Update the database with the new file path
        if os.path.exists(dest_path):
            new_hash = self.monitor.calculate_file_hash(dest_path)
            stats = os.stat(dest_path)
            self.monitor.db.store_file_hash(
                dest_path,
                new_hash,
                datetime.fromtimestamp(stats.st_mtime).isoformat(),
                str(oct(stats.st_mode)[-3:]),
            )

    def _handle_file_event(self, file_path, event_type):
        file_path_clean = self.format_path(file_path)
        if event_type != "DELETED":
            new_hash = self.monitor.calculate_file_hash(file_path)
            old_hash = self.monitor.db.get_file_hash(file_path)

            if old_hash != new_hash:
                alert_msg = f"File {event_type}: {file_path_clean}"
                if event_type == "CREATED":
                    console.print(f"[green]{alert_msg}[/green]")
                elif event_type == "MODIFIED":
                    console.print(f"[blue]{alert_msg}[/blue]")

                self.monitor.db.log_alert(
                    file_path, event_type, f"Hash changed: {old_hash} -> {new_hash}"
                )

                if event_type != "DELETED":
                    stats = os.stat(file_path)
                    self.monitor.db.store_file_hash(
                        file_path,
                        new_hash,
                        datetime.fromtimestamp(stats.st_mtime).isoformat(),
                        str(oct(stats.st_mode)[-3:]),
                    )
        else:
            alert_msg = f"File {event_type}: {file_path_clean}"
            console.print(f"[red]{alert_msg}[/red]")
            self.monitor.db.log_alert(file_path, event_type, "File deleted")


def main():
    try:
        path_to_monitor = clean_path(input("Enter the directory path to monitor: "))
        if not os.path.exists(path_to_monitor):
            console.print("[red]Directory does not exist![/red]")
            return

        monitor = FileMonitor(path_to_monitor)
        monitor.establish_baseline()

        event_handler = FileEventHandler(monitor)
        observer = Observer()
        observer.schedule(event_handler, path_to_monitor, recursive=True)
        observer.start()

        start_time = datetime.now()
        console.print(
            f"[green]Started monitoring at {start_time.strftime('%Y-%m-%d %H:%M:%S')}. Press 'q' to stop...[/green]"
        )

        while True:
            if get_key() == "q":
                break
            time.sleep(0.1)  # Prevent high CPU usage

        # Countdown starts only after 'q' is pressed
        console.print("[yellow]Stopping monitor in 3 seconds...[/yellow]")
        for i in range(3, 0, -1):
            time.sleep(1)
            console.print(f"[yellow]{i}...[/yellow]")

        observer.stop()
        console.print("[yellow]Monitor stopped.[/yellow]")
        observer.join()

        log_count = len(monitor.db.get_all_alerts())
        console.print(f"\n[cyan]Total file events logged: {log_count}[/cyan]")

        # Skip export prompt if no logs exist
        if log_count == 0:
            console.print(
                "[yellow]No events detected. Skipping export prompt.[/yellow]"
            )
        else:
            export_choice = (
                input("\nWould you like to export the logs? (y/n/both): ")
                .lower()
                .strip()
            )
            if export_choice in ["y", "yes"]:
                export_logs(monitor)
            elif export_choice in ["b", "both"]:
                console.print("[yellow]Exporting logs as both CSV and PDF...[/yellow]")
                export_to_csv(monitor)
                export_to_pdf(monitor)

        console.print("[green]Monitoring stopped successfully.[/green]")

        console.print("\n[cyan]Session Summary:[/cyan]")
        console.print(f"Directory monitored: [yellow]{path_to_monitor}[/yellow]")
        console.print(f"Total file events logged: {log_count}")

        duration = datetime.now() - start_time
        console.print(f"Monitoring duration: {str(duration).split('.')[0]}")

    except Exception as e:
        console.print(f"[red]An error occurred: {str(e)}[/red]")
    finally:
        try:
            observer.stop()
            observer.join()
        except Exception:
            pass


if __name__ == "__main__":
    main()
