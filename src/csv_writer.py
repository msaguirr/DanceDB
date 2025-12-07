import csv
import shutil
import os
import csv
import shutil
import os


class CSVDatabase:
    def __init__(self, filename, fieldnames):
        self.filename = filename
        self.fieldnames = fieldnames
        # Ensure the file exists and has headers
        if not os.path.exists(self.filename) or os.stat(self.filename).st_size == 0:
            with open(self.filename, mode='w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=self.fieldnames)
                writer.writeheader()

    def _read_all_rows(self):
        """Helper to read all data as a list of dictionaries."""
        with open(self.filename, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            return list(reader)

    def _write_all_rows(self, data):
        """Helper to overwrite the entire file with new data."""
        with open(self.filename, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=self.fieldnames)
            writer.writeheader()
            writer.writerows(data)

    def add_record(self, record_dict):
        """Adds a new record to the end of the file."""
        # Append mode is more efficient for simply adding
        with open(self.filename, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=self.fieldnames)
            writer.writerow(record_dict)
        print(f"Added record: {record_dict}")

    def delete_record(self, key_field, key_value):
        """Deletes all records matching the key_field and key_value."""
        data = self._read_all_rows()
        original_count = len(data)
        # Filter out rows where the key field matches the value
        updated_data = [row for row in data if row.get(key_field) != key_value]

        if len(updated_data) < original_count:
            self._write_all_rows(updated_data)
            print(f"Deleted records where {key_field} was '{key_value}'.")
        else:
            print(f"No records found to delete with {key_field}='{key_value}'.")

    def update_records(self, key_field, key_value, updates_dict):
        """Updates records matching the key_field/key_value with new values."""
        data = self._read_all_rows()
        updated_count = 0
        for row in data:
            if row.get(key_field) == key_value:
                row.update(updates_dict)
                updated_count += 1
        
        if updated_count > 0:
            self._write_all_rows(data)
            print(f"Updated {updated_count} records where {key_field} was '{key_value}'.")
        else:
            print(f"No records found to update with {key_field}='{key_value}'.")

    def view_all(self):
        """Prints all current records in the database."""
        data = self._read_all_rows()
        print("\nCurrent Database Contents:")
        for row in data:
            print(row)
        print("-" * 20)


