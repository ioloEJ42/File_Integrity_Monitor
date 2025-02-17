# File Integrity Monitor (FIM)

## Overview

File Integrity Monitor (**FIM.py**) is a Python-based tool that monitors a directory for any file changes, including creation, modification, renaming, and deletion. It uses the **watchdog** library to detect file system events and logs them in an SQLite database. Additionally, the tool supports exporting logs to **CSV** and **PDF** formats for further analysis.

## Features

- **Real-time File Monitoring:** Tracks changes in files within the specified directory.
- **Logging to Database:** Stores file events (modification, creation, deletion, renaming) in an SQLite database.
- **File Hashing:** Uses SHA-256 to detect content changes in modified files.
- **Export Logs:** Allows exporting log data to **CSV** and **PDF** formats.
- **User-friendly Console Output:** Provides real-time status updates using **rich** for colored terminal output.

---

## Installation

### Prerequisites

Ensure you have **Python 3.6+** installed on your system.

### Required Dependencies

Install the required Python packages using:

```sh
pip install watchdog rich reportlab
```

---

## How to Use

### 1. Start the File Integrity Monitor

Run the script and provide the directory to monitor:

```sh
python FIM.py
```

Follow the prompt to enter the directory path. The tool will begin monitoring file activities.

### 2. Stopping the Monitor

Press **'q'** to stop monitoring.

### 3. Exporting Logs

Once monitoring stops, you will be prompted to export logs:

- **CSV format:** `fim_logs_YYYYMMDD_HHMMSS.csv`
- **PDF format:** `fim_logs_YYYYMMDD_HHMMSS.pdf`

---

## Testing the File Integrity Monitor

To test the functionality, use the provided testing script **tester_FIM.py**.

### Running the Tester

```sh
python tester_FIM.py
```

### How It Works

- The script randomly **creates, modifies, renames, and deletes files** in the monitored directory.
- The FIM tool should **detect and log all these changes.**

### Test Parameters

Upon running `tester_FIM.py`, you will be prompted to enter:

1. **Directory to test:** (Must match the one used in `FIM.py`)
2. **Duration of the test:** (Default: 60 seconds)
3. **Interval between operations:** (Default: 5 seconds)

The tester will then perform random file operations for the specified duration.

---

## Example Output

**When a file is created:**

```
[green]File CREATED: /path/to/file/test_1234.txt[/green]
```

**When a file is modified:**

```
[blue]File MODIFIED: /path/to/file/test_1234.txt[/blue]
```

**When a file is renamed:**

```
[yellow]File RENAMED: /path/to/file/test_1234.txt -> /path/to/file/renamed_5678.txt[/yellow]
```

**When a file is deleted:**

```
[red]File DELETED: /path/to/file/test_1234.txt[/red]
```

---

## Troubleshooting

### Common Issues & Fixes

| Issue                           | Solution                                                                              |
| ------------------------------- | ------------------------------------------------------------------------------------- |
| **FIM does not detect changes** | Ensure that the provided directory exists and that you have permission to monitor it. |
| **Database file not created**   | Ensure the script has write permissions in the working directory.                     |
| **High CPU usage**              | Reduce the polling frequency (`time.sleep(0.5)`) in `main()` function.                |
| **PDF export fails**            | Ensure `reportlab` is installed (`pip install reportlab`).                            |

---

## Conclusion

This File Integrity Monitor (FIM) is a useful tool for detecting unauthorized file changes in a directory. It provides **real-time monitoring**, **logs all file events**, and supports **exporting logs for analysis.** Use `tester_FIM.py` to validate its effectiveness in detecting file changes.

---

## License

This project is released under the **MIT License**. Feel free to modify and use it for personal or educational purposes.
