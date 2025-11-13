"""
Celery Background Tasks.
"""

from auditor_pro import celery, db, celery as app, mail
from flask_mail import Message
from flask_socketio import SocketIO
from auditor_pro.config import config
from auditor_pro.models import AuditReport, AuditResult, BrokenLink, Project, User
import requests
from bs4 import BeautifulSoup
# --- We need these imports at the top ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
# ---------------------------------------
from datetime import datetime
import subprocess
import json
import tempfile
import os
from urllib.parse import urljoin, urlparse
from datetime import timedelta
from .models import Project


# --- THIS IS THE FIX ---
# We just define the variable, but we don't *run* the install here.
DRIVER_PATH = None

def get_page_content_task(url):
    """
    Fetches and parses the content of a URL *for a task*.
    """
    global DRIVER_PATH

    start_time = time.time()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    soup = None
    method = "requests"
    try:
        session = requests.Session()
        page = session.get(url, headers=headers, timeout=10)
        page.raise_for_status()
        soup = BeautifulSoup(page.content, 'html.parser')
        links = soup.find_all('a')
        images = soup.find_all('img')
        if len(links) < 10 and len(images) < 3:
            print("Requests got an empty shell, forcing Selenium...")
            soup = None
    except Exception as e:
        print(f"Requests failed ({type(e).__name__}), trying Selenium...")

    if soup is None:
        method = "selenium"

        # --- THIS IS THE FIX ---
        # We now initialize the driver *inside* the task, only if needed.
        if not DRIVER_PATH:
            try:
                print("Celery worker initializing WebDriver manager for the first time...")
                DRIVER_PATH = ChromeDriverManager().install()
                print(f"Celery worker cached WebDriver at: {DRIVER_PATH}")
            except Exception as e:
                print(f"CRITICAL: Celery worker failed to initialize WebDriver: {e}")
                return None, "selenium", "SELENIUM_ERROR: WebDriver failed to initialize."

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = None
        try:
            driver = webdriver.Chrome(service=Service(DRIVER_PATH), options=chrome_options)
            driver.get(url)
            time.sleep(3)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
        except Exception as e:
            return None, "selenium", f"SELENIUM_ERROR: {str(e)}"
        finally:
            if driver:
                driver.quit()
    if soup is None:
        return None, method, "UNKNOWN_ERROR: Both methods failed to get content."
    print(f"Audit Task: Got content from {url} using {method}")
    return soup, method, None

def analyze_page_task(soup):
    results = []
    seo_fail_points = 0
    total_seo_checks = 0
    a11y_fail_points = 0
    total_a11y_checks = 0
    def add_check(category, status, title, message, fail_points=1):
        results.append({
            'category': category, 'status': status,
            'title': title, 'message': message
        })
        if category == 'seo':
            return 0 if status in ['pass', 'warn'] else fail_points
        if category == 'accessibility':
            return 0 if status in ['pass', 'warn'] else fail_points
        return 0
    title_tag = soup.find('title')
    title_text = title_tag.string.strip() if title_tag and title_tag.string else ""
    desc_tag = soup.find('meta', attrs={'name': 'description'})
    desc_text = desc_tag.get('content', '').strip() if desc_tag else ""
    h1s = soup.find_all('h1')
    total_seo_checks += 1
    if not title_text:
        seo_fail_points += add_check('seo', 'fail', 'Title Tag', 'FAIL: No <title> tag found.')
    elif 20 <= len(title_text) <= 60:
        seo_fail_points += add_check('seo', 'pass', 'Title Length', f"PASS: Title is {len(title_text)} characters long.")
    else:
        seo_fail_points += add_check('seo', 'warn', 'Title Length', f"WARN: Title is {len(title_text)} characters. Recommended length is 20-60.")
    total_seo_checks += 1
    if not desc_text:
        seo_fail_points += add_check('seo', 'fail', 'Meta Description', 'FAIL: No <meta name="description"> tag found.')
    elif 50 <= len(desc_text) <= 160:
        seo_fail_points += add_check('seo', 'pass', 'Meta Description', f"PASS: Meta description is {len(desc_text)} characters.")
    else:
        seo_fail_points += add_check('seo', 'warn', 'Meta Description', f"WARN: Meta description is {len(desc_text)} characters. Recommended length is 50-160.")
    total_seo_checks += 1
    if len(h1s) == 0:
        seo_fail_points += add_check('seo', 'fail', 'H1 Tag', 'FAIL: No <h1> tag found.')
    elif len(h1s) > 1:
        seo_fail_points += add_check('seo', 'warn', 'H1 Tag', f"WARN: {len(h1s)} <h1> tags found. Only one is recommended.")
    else:
        seo_fail_points += add_check('seo', 'pass', 'H1 Tag', 'PASS: Exactly one <h1> tag was found.')
    total_seo_checks += 1
    if soup.find('meta', attrs={'name': 'viewport'}):
        seo_fail_points += add_check('seo', 'pass', 'Mobile Viewport', 'PASS: A mobile viewport meta tag is present.')
    else:
        seo_fail_points += add_check('seo', 'fail', 'Mobile Viewport', 'FAIL: Missing a <meta name="viewport"> tag. This is critical for mobile SEO.')
    total_seo_checks += 1
    og_title = soup.find('meta', property='og:title')
    og_desc = soup.find('meta', property='og:description')
    if og_title and og_desc:
        seo_fail_points += add_check('seo', 'pass', 'Social (Open Graph)', 'PASS: Found `og:title` and `og:description` tags for social media sharing.')
    else:
        seo_fail_points += add_check('seo', 'warn', 'Social (Open Graph)', 'WARN: Missing `og:title` or `og:description` tags. This will look bad when shared on social media.')
    total_a11y_checks += 1
    if soup.find('html', lang=True):
        a11y_fail_points += add_check('accessibility', 'pass', 'HTML Language', 'PASS: The `<html>` tag has a "lang" attribute.')
    else:
        a11y_fail_points += add_check('accessibility', 'fail', 'HTML Language', 'FAIL: The `<html>` tag is missing a "lang" attribute.')
    total_a11y_checks += 1
    images = soup.find_all('img')
    missing_alt = sum(1 for img in images if not img.get('alt', '').strip())
    if len(images) == 0:
        a11y_fail_points += add_check('accessibility', 'pass', 'Image Alt Text', 'PASS: No images found on the page.')
    elif missing_alt == 0:
        a11y_fail_points += add_check('accessibility', 'pass', 'Image Alt Text', f"PASS: All {len(images)} images have alt text.")
    else:
        a11y_fail_points += add_check('accessibility', 'fail', 'Image Alt Text', f"FAIL: {missing_alt} of {len(images)} images are missing descriptive alt text.")
    total_a11y_checks += 1
    inputs = soup.find_all(['input', 'textarea', 'select'])
    missing_labels = 0
    for el in inputs:
        if el.get('type') == 'hidden': continue
        if not (el.get('id') and soup.find('label', {'for': el.get('id')})):
            missing_labels += 1
    if len(inputs) == 0:
         a11y_fail_points += add_check('accessibility', 'pass', 'Form Labels', 'PASS: No form inputs found.')
    elif missing_labels == 0:
        a11y_fail_points += add_check('accessibility', 'pass', 'Form Labels', f"PASS: All {len(inputs)} form inputs have associated labels.")
    else:
        a11y_fail_points += add_check('accessibility', 'warn', 'Form Labels', f"WARN: {missing_labels} form inputs may be missing an associated <label>.")
    seo_score = max(0, round(((total_seo_checks - seo_fail_points) / total_seo_checks) * 100)) if total_seo_checks > 0 else 100
    a11y_score = max(0, round(((total_a11y_checks - a11y_fail_points) / total_a11y_checks) * 100)) if total_a11y_checks > 0 else 100
    overall_score = round((seo_score + a11y_score) / 2)
    scores = {'seo': seo_score, 'accessibility': a11y_score, 'overall': overall_score}
    return results, scores

def run_lighthouse_task(url):
    results = []
    scores = {
        'performance': 0, 'lcp': 0, 'cls': 0, 'fid': 0
    }
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_file:
        output_path = tmp_file.name
    try:
        command = [
            "lighthouse",
            url,
            "--output=json",
            f"--output-path={output_path}",
            "--only-categories=performance",
            "--chrome-flags=--headless --no-sandbox"
        ]
        print(f"Lighthouse Task: Running command: {' '.join(command)}")
        subprocess.run(command, check=True, timeout=90)
        with open(output_path, 'r') as f:
            report_data = json.load(f)
        scores['performance'] = int(report_data['categories']['performance']['score'] * 100)
        lcp_metric = report_data['audits']['largest-contentful-paint']
        cls_metric = report_data['audits']['cumulative-layout-shift']
        fid_metric = report_data['audits']['max-potential-fid']
        scores['lcp'] = round(lcp_metric.get('numericValue', 0) / 1000, 2)
        scores['cls'] = round(cls_metric.get('numericValue', 0), 3)
        scores['fid'] = int(fid_metric.get('numericValue', 0))
        results.append({
            'category': 'performance',
            'status': lcp_metric.get('scoreDisplayMode', 'info'),
            'title': 'Largest Contentful Paint (LCP)',
            'message': f"{lcp_metric.get('displayValue', 'N/A')}. This is the time it takes to load the largest element on the page."
        })
        results.append({
            'category': 'performance',
            'status': cls_metric.get('scoreDisplayMode', 'info'),
            'title': 'Cumulative Layout Shift (CLS)',
            'message': f"{cls_metric.get('displayValue', 'N/A')}. This measures how much your page content unexpectedly shifts around."
        })
        results.append({
            'category': 'performance',
            'status': fid_metric.get('scoreDisplayMode', 'info'),
            'title': 'Max Potential First Input Delay (FID)',
            'message': f"{fid_metric.get('displayValue', 'N/A')}. This measures your page's responsiveness to user interaction."
        })
        print(f"Lighthouse Task: Success. Score: {scores['performance']}")
    except subprocess.TimeoutExpired:
        print("Lighthouse Task: FAILED (Timeout)")
        raise Exception("Lighthouse audit timed out after 90 seconds.")
    except Exception as e:
        print(f"Lighthouse Task: FAILED ({e})")
        raise Exception(f"Lighthouse audit failed. Make sure 'lighthouse' is installed globally. Error: {e}")
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)
    return results, scores

def run_link_crawler_task(soup, base_url):
    print("Link Crawler: Starting...")
    broken_links = []
    internal_links = set()
    base_domain = urlparse(base_url).netloc
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    for link in soup.find_all('a', href=True):
        href = link['href']
        if not href or href.startswith(('#', 'mailto:', 'tel:')):
            continue
        absolute_url = urljoin(base_url, href)
        link_domain = urlparse(absolute_url).netloc
        if link_domain == base_domain and absolute_url not in internal_links:
            internal_links.add(absolute_url)
            try:
                response = requests.head(absolute_url, headers=headers, timeout=5, allow_redirects=True)
                if response.status_code >= 400:
                    print(f"Link Crawler: FOUND BROKEN LINK: {absolute_url} (Status: {response.status_code})")
                    broken_links.append({
                        'link_url': absolute_url,
                        'status_code': response.status_code
                    })
            except requests.exceptions.Timeout:
                print(f"Link Crawler: FOUND BROKEN LINK: {absolute_url} (Status: Timeout)")
                broken_links.append({
                    'link_url': absolute_url,
                    'status_code': 504
                })
            except requests.exceptions.RequestException:
                print(f"Link Crawler: FOUND BROKEN LINK: {absolute_url} (Status: Connection Error)")
                broken_links.append({
                    'link_url': absolute_url,
                    'status_code': 503
                })
    print(f"Link Crawler: Finished. Found {len(broken_links)} broken links.")
    return broken_links

@celery.task
def send_alert_email_task(user_email, project_name, old_score, new_score):
    """
    Sends an email alert to the user about a score drop.
    """
    try:
        subject = f"Alert: Your score for '{project_name}' has dropped!"
        body = f"""
        Hello,
        
        This is an automated alert from Page Auditor Pro.
        
        The overall score for your project '{project_name}' has dropped significantly in its latest audit.
        
        Previous Score: {old_score}/100
        New Score: {new_score}/100
        
        Please log in to your dashboard to view the full report and see what changed.
        
        - The Page Auditor Pro Team
        """
        msg = Message(subject, recipients=[user_email], body=body)
        mail.send(msg)
        print(f"EMAIL: Sent score drop alert to {user_email} for project '{project_name}'")
    except Exception as e:
        print(f"EMAIL: FAILED to send alert to {user_email}: {e}")

def _get_socketio_client():
    """
    Creates a new SocketIO client instance that can emit
    messages from a Celery worker, by connecting
    directly to the Redis message queue.
    """
    message_queue = config['default'].CELERY_BROKER_URL
    return SocketIO(message_queue=message_queue)


@celery.task(bind=True)
def run_audit_task(self, report_id, url):
    """
    This is the main background task.
    """

    report = AuditReport.query.get(report_id)
    if not report:
        print(f"ERROR: AuditReport {report_id} not found.")
        return

    project = report.project
    user = project.owner

    previous_report = project.reports.filter(
        AuditReport.id != report.id,
        AuditReport.status == 'COMPLETE'
    ).order_by(AuditReport.created_at.desc()).first()
    old_score = previous_report.overall_score if previous_report else None

    try:
        report.status = 'RUNNING'
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error setting report to RUNNING: {e}")
        return

    try:
        print(f"Audit {report_id}: Starting HTML audit & Link Crawl...")
        soup, method, error = get_page_content_task(url)
        if error: raise Exception(f"HTML fetch failed: {error}")
        html_results, html_scores = analyze_page_task(soup)
        broken_links_list = run_link_crawler_task(soup, url)

        print(f"Audit {report_id}: Starting Lighthouse audit...")
        perf_results, perf_scores = run_lighthouse_task(url)

        report.status = 'COMPLETE'
        report.seo_score = html_scores['seo']
        report.a11y_score = html_scores['accessibility']
        report.performance_score = perf_scores['performance']
        report.lcp = perf_scores['lcp']
        report.cls = perf_scores['cls']
        report.fid = perf_scores['fid']
        report.overall_score = round(
            (html_scores['seo'] + html_scores['accessibility'] + perf_scores['performance']) / 3
        )

        all_db_objects = []
        for res in (html_results + perf_results):
            all_db_objects.append(AuditResult(
                report_id=report.id, category=res['category'],
                status=res['status'], title=res['title'], message=res['message']
            ))
        for link in broken_links_list:
            all_db_objects.append(BrokenLink(
                report_id=report.id,
                link_url=link['link_url'], status_code=link['status_code']
            ))
        db.session.add_all(all_db_objects)
        db.session.commit()

        print(f"SUCCESS: Audit {report_id} complete. Overall: {report.overall_score}, Perf: {report.performance_score}")

        if old_score and report.overall_score < (old_score - 10):
            print(f"ALERT: Score for '{project.name}' dropped from {old_score} to {report.overall_score}. Queuing email.")
            send_alert_email_task.delay(
                user.email, project.name, old_score, report.overall_score
            )

        schedule_text = f" ({project.schedule.title()})" if project.schedule != 'none' else ""
        new_status_string = f"Score: {report.overall_score}/100 | Perf: {report.performance_score}/100{schedule_text}"
        event_data = {
            'project_id': project.id,
            'new_status': new_status_string,
            'report_id': report.id
        }

        socketio_client = _get_socketio_client()
        print(f"WEBSOCKET: Emitting 'audit_complete' to room 'user_{user.id}'")
        socketio_client.emit('audit_complete', event_data, room=f'user_{user.id}')

    except Exception as e:
        db.session.rollback()
        report.status = 'FAILED'
        report.error_message = str(e)[:250]
        db.session.commit()

        event_data = {
            'project_id': project.id,
            'new_status': 'Audit Failed',
            'report_id': report.id
        }
        socketio_client = _get_socketio_client()
        socketio_client.emit('audit_complete', event_data, room=f'user_{user.id}')

        print(f"FAIL: Audit {report_id} failed: {e}")


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        timedelta(hours=1),
        queue_scheduled_audits.s(),
        name='Check for scheduled audits every hour'
    )

@celery.task
def queue_scheduled_audits():
    print("SCHEDULER: Running hourly check for scheduled audits...")
    daily_projects = Project.query.filter_by(schedule='daily').all()
    weekly_projects = Project.query.filter_by(schedule='weekly').all()
    projects_to_queue = []
    for project in daily_projects:
        latest_report = project.reports.order_by(AuditReport.created_at.desc()).first()
        if not latest_report or (datetime.utcnow() - latest_report.created_at) > timedelta(hours=23):
            projects_to_queue.append(project)
    for project in weekly_projects:
        latest_report = project.reports.order_by(AuditReport.created_at.desc()).first()
        # --- FIX THE TYPO: latest_track -> latest_report ---
        if not latest_report or (datetime.utcnow() - latest_report.created_at) > timedelta(days=6):
            projects_to_queue.append(project)
    if not projects_to_queue:
        print("SCHEDULER: No projects due for an audit.")
        return
    print(f"SCHEDULER: Found {len(projects_to_queue)} projects due for an audit. Queuing now...")
    for project in projects_to_queue:
        try:
            new_report = AuditReport(
                project_id=project.id,
                status='PENDING'
            )
            db.session.add(new_report)
            db.session.commit()
            run_audit_task.delay(new_report.id, project.base_url)
            print(f"SCHEDULER: Queued audit for '{project.name}' (Report ID: {new_report.id})")
        except Exception as e:
            db.session.rollback()
            print(f"SCHEDULER: Error queuing audit for '{project.name}': {e}")