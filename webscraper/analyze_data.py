import pandas as pd
import matplotlib.pyplot as plt


def debug_csv():
    print("=== DEBUGGING CSV FILE ===")

    # Let's read the file line by line to see what's wrong
    with open('scraped_data.csv', 'r', encoding='utf-8') as file:
        for i, line in enumerate(file):
            print(f"Line {i + 1}: {line.strip()}")
            if i > 10:  # Only show first 10 lines
                break


def analyze_scraped_data():
    # Read the CSV file with error handling
    try:
        # Try to read with different options to handle messy data
        df = pd.read_csv('scraped_data.csv', on_bad_lines='skip')  # Skip bad lines
        print("✅ Successfully loaded your scraped data!")
        print(f"📊 Total websites scraped: {len(df)}")
        print()

        # Show the column names to see what we have
        print("=== COLUMNS IN YOUR DATA ===")
        print(df.columns.tolist())
        print()

        # Show basic information about your data
        print("=== BASIC DATA INFO ===")
        print(df.head())  # Shows first 5 rows
        print()

        # Find interesting patterns
        print("=== INTERESTING PATTERNS ===")

        # Check if we have the expected columns
        if 'num_links' in df.columns:
            # Which site has the most links?
            max_links_site = df.loc[df['num_links'].idxmax()]
            print(f"🔗 Site with most links: {max_links_site['url']} ({max_links_site['num_links']} links)")

        if 'total_images' in df.columns:
            # Which site has the most images?
            max_images_site = df.loc[df['total_images'].idxmax()]
            print(f"🖼️  Site with most images: {max_images_site['url']} ({max_images_site['total_images']} images)")

        if 'page_size_kb' in df.columns:
            # Which site is biggest?
            biggest_site = df.loc[df['page_size_kb'].idxmax()]
            print(f"📏 Biggest site: {biggest_site['url']} ({biggest_site['page_size_kb']} KB)")

        # Show averages if columns exist
        numeric_columns = df.select_dtypes(include=['number']).columns
        for col in numeric_columns:
            if 'num_' in col or 'total_' in col or 'page_size' in col:
                print(f"📊 Average {col}: {df[col].mean():.1f}")

    except FileNotFoundError:
        print("❌ No scraped_data.csv found. Scrape some websites first!")
    except Exception as e:
        print(f"❌ Error reading data: {e}")
        print("\nLet's debug the CSV file:")
        debug_csv()


if __name__ == "__main__":
    analyze_scraped_data()