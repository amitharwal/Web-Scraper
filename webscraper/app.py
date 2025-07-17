from flask import Flask, render_template, request, send_file
from scraper import scrape
import pandas as pd
import os

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


@app.route('/analysis')
def analysis():
    try:
        # Check if CSV file exists
        if not os.path.exists('scraped_data.csv'):
            return render_template('analysis.html', has_data=False)

        df = pd.read_csv('scraped_data.csv', on_bad_lines='skip')

        if len(df) == 0:
            return render_template('analysis.html', has_data=False)

        # Calculate statistics
        stats = {
            'total_sites': len(df),
            'avg_links': round(df['num_links'].mean(), 1),
            'avg_images': round(df['total_images'].mean(), 1),
            'avg_size': round(df['page_size_kb'].mean(), 1),
            'most_links_site': df.loc[df['num_links'].idxmax()].to_dict(),
            'most_images_site': df.loc[df['total_images'].idxmax()].to_dict(),
            'biggest_site': df.loc[df['page_size_kb'].idxmax()].to_dict(),
            'recent_sites': df.tail(10).to_dict('records')  # Last 10 sites
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
    app.run(debug=True)