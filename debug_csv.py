import pandas as pd
import csv


def debug_csv_file():
    print("=== DEBUGGING CSV FILE ===")

    # Method 1: Read raw file
    print("\n1. RAW FILE CONTENTS:")
    try:
        with open('scraped_data.csv', 'r', encoding='utf-8') as file:
            for i, line in enumerate(file):
                print(f"Line {i + 1}: '{line.strip()}'")
                if i > 5:  # Only show first 6 lines
                    break
    except Exception as e:
        print(f"Error reading file: {e}")

    # Method 2: Try pandas with different options
    print("\n2. PANDAS READING TEST:")
    try:
        df = pd.read_csv('scraped_data.csv', on_bad_lines='skip')
        print(f"✅ Pandas read {len(df)} rows successfully")
        print(f"Columns: {df.columns.tolist()}")
        if len(df) > 0:
            print(f"First row: {df.iloc[0].to_dict()}")
    except Exception as e:
        print(f"❌ Pandas error: {e}")

    # Method 3: Try with csv module
    print("\n3. CSV MODULE TEST:")
    try:
        with open('scraped_data.csv', 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for i, row in enumerate(reader):
                print(f"Row {i + 1}: {len(row)} fields - {row}")
                if i > 3:
                    break
    except Exception as e:
        print(f"❌ CSV module error: {e}")


if __name__ == "__main__":
    debug_csv_file()