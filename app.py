from flask import Flask, render_template, request, send_file
from scraper import scrape
import os
import json

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('main.html')


@app.route('/scrape', methods=['GET', 'POST'])
def url_form():
    if request.method == 'POST':
        url = request.form['userLink']
        print(f"User submitted url: {url}")

        result = scrape(url)

        if isinstance(result, dict):
            return render_template('results.html',
                                   url=url,
                                   success=True,
                                   title=result.get('title'),
                                   description=result.get('meta'),
                                   headlines=result.get('headlines'),
                                   links=result.get('links'),
                                   stats=result.get('stats', {}))
        else:
            return render_template('results.html',
                                   url=url,
                                   success=False,
                                   error_message=result)

    return render_template('main.html')


@app.route('/analysis')
def analysis():
    try:
        # Check if CSV file exists
        if not os.path.exists('scraped_data.csv'):
            return render_template('analysis.html', has_data=False)

        # Simple CSV reading without pandas
        import csv
        data = []
        with open('scraped_data.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Convert numeric fields
                for field in ['num_headlines', 'num_links', 'total_elements', 'total_images', 'page_size_kb']:
                    if field in row:
                        try:
                            if field == 'page_size_kb':
                                row[field] = float(row[field])
                            else:
                                row[field] = int(row[field])
                        except:
                            row[field] = 0
                data.append(row)

        if len(data) == 0:
            return render_template('analysis.html', has_data=False)

        # Calculate statistics manually
        total_sites = len(data)
        avg_links = sum(row.get('num_links', 0) for row in data) / total_sites if total_sites > 0 else 0
        avg_images = sum(row.get('total_images', 0) for row in data) / total_sites if total_sites > 0 else 0
        avg_size = sum(row.get('page_size_kb', 0) for row in data) / total_sites if total_sites > 0 else 0

        # Find max values
        most_links_site = max(data, key=lambda x: x.get('num_links', 0))
        most_images_site = max(data, key=lambda x: x.get('total_images', 0))
        biggest_site = max(data, key=lambda x: x.get('page_size_kb', 0))

        stats = {
            'total_sites': total_sites,
            'avg_links': round(avg_links, 1),
            'avg_images': round(avg_images, 1),
            'avg_size': round(avg_size, 1),
            'most_links_site': most_links_site,
            'most_images_site': most_images_site,
            'biggest_site': biggest_site,
            'recent_sites': data[-10:]  # Last 10 sites
        }

        return render_template('analysis.html', has_data=True, **stats)

    except Exception as e:
        print(f"Error in analysis: {e}")
        return render_template('analysis.html', has_data=False)


@app.route('/download-csv')
def download_csv():
    try:
        return send_file('scraped_data.csv', as_attachment=True, download_name='my_scraped_data.csv')
    except FileNotFoundError:
        return "No data available for download", 404


if __name__ == '__main__':
    # Use PORT from environment variable for deployment
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)