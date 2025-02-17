import os
import time
import random
import string
from datetime import datetime


class FIMTester:
    def __init__(self, test_dir):
        self.test_dir = test_dir
        self.created_files = []

        # Create test directory if it doesn't exist
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)

    def generate_random_content(self):
        """Generate random text content"""
        return "".join(
            random.choices(
                string.ascii_letters + string.digits, k=random.randint(50, 200)
            )
        )

    def create_random_file(self):
        """Create a new file with random content"""
        filename = (
            f"test_{datetime.now().strftime('%H%M%S')}_{random.randint(1000, 9999)}.txt"
        )
        filepath = os.path.join(self.test_dir, filename)

        with open(filepath, "w") as f:
            f.write(self.generate_random_content())

        self.created_files.append(filepath)
        print(f"Created: {filepath}")
        return filepath

    def modify_random_file(self):
        """Modify a random existing file"""
        if not self.created_files:
            return None

        target_file = random.choice(self.created_files)
        if os.path.exists(target_file):
            with open(target_file, "a") as f:
                f.write("\n" + self.generate_random_content())
            print(f"Modified: {target_file}")
            return target_file
        return None

    def rename_random_file(self):
        """Rename a random existing file"""
        if not self.created_files:
            return None

        source_file = random.choice(self.created_files)
        if os.path.exists(source_file):
            # Randomly choose between renaming with same or different extension
            if random.choice([True, False]):
                new_name = f"renamed_{datetime.now().strftime('%H%M%S')}_{random.randint(1000, 9999)}.txt"
            else:
                new_name = f"renamed_{datetime.now().strftime('%H%M%S')}_{random.randint(1000, 9999)}.log"

            new_path = os.path.join(self.test_dir, new_name)
            os.rename(source_file, new_path)
            self.created_files.remove(source_file)
            self.created_files.append(new_path)
            print(f"Renamed: {source_file} -> {new_path}")
            return new_path
        return None

    def delete_random_file(self):
        """Delete a random existing file"""
        if not self.created_files:
            return None

        target_file = random.choice(self.created_files)
        if os.path.exists(target_file):
            os.remove(target_file)
            self.created_files.remove(target_file)
            print(f"Deleted: {target_file}")
            return target_file
        return None

    def run_test_sequence(self, duration_seconds=60, interval_seconds=5):
        """Run a sequence of random file operations"""
        print(f"Starting test sequence for {duration_seconds} seconds...")
        end_time = time.time() + duration_seconds

        while time.time() < end_time:
            # Randomly choose an operation
            operation = random.choice(
                [
                    self.create_random_file,
                    self.modify_random_file,
                    self.rename_random_file,
                    self.delete_random_file,
                ]
            )

            # Execute the chosen operation
            operation()

            # Wait for the specified interval
            time.sleep(interval_seconds)


def clean_path(path):
    """Clean the input path by removing quotes and extra spaces and converting to proper path format"""
    path = path.strip().strip('"').strip("'").strip()

    # If running in WSL and a Windows path is provided, convert it
    if os.name != "nt" and path.startswith(("C:", "D:", "E:")):
        # Convert Windows path to WSL path
        drive_letter = path[0].lower()
        win_path = path[3:].replace("\\", "/")
        wsl_path = f"/mnt/{drive_letter}/{win_path}"
        return os.path.abspath(wsl_path)  # Ensure we have absolute path

    # For Windows, convert forward slashes to backslashes
    elif os.name == "nt":
        return os.path.abspath(path.replace("/", "\\"))  # Ensure we have absolute path

    return os.path.abspath(path)  # Ensure we have absolute path


def main():
    try:
        test_dir = clean_path(
            input("Enter the directory path for testing (same as FIM): ")
        )
        test_dir = os.path.abspath(test_dir)  # Ensure absolute path

        if not os.path.exists(test_dir):
            print(f"Creating directory: {test_dir}")
            os.makedirs(test_dir, exist_ok=True)

        test_duration = int(
            input("Enter test duration in seconds (default 60): ") or "60"
        )
        interval = int(
            input("Enter interval between operations in seconds (default 5): ") or "5"
        )

        print(f"Using test directory: {test_dir}")  # Debug output
        tester = FIMTester(test_dir)
        tester.run_test_sequence(test_duration, interval)
        print("Test sequence completed!")

    except Exception as e:
        print(f"Error during test execution: {e}")
        raise


if __name__ == "__main__":
    main()
