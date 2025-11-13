"""
Main Application Routes.
Defines the homepage (/), the user dashboard (/dashboard),
and project-related actions.
"""

import json
from weasyprint import HTML
from flask import Response
from flask import render_template, redirect, url_for, request, flash, abort, jsonify
from flask_login import login_required, current_user
from . import main_bp
from auditor_pro.models import Project, AuditReport, AuditResult
from auditor_pro import db, socketio
from flask_socketio import join_room

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    projects = Project.query.filter_by(user_id=current_user.id)\
                           .order_by(Project.created_at.desc())\
                           .all()
    return render_template('dashboard.html', projects=projects)

@main_bp.route('/create-project', methods=['POST'])
@login_required
def create_project():
    if request.method == 'POST':
        project_name = request.form.get('project_name')
        project_url = request.form.get('project_url')
        if not project_name or not project_url:
            flash('Project Name and URL are required.', 'danger')
            return redirect(url_for('main.dashboard'))
        if not project_url.startswith(('http://', 'https://')):
            project_url = 'https://' + project_url
        new_project = Project(
            name=project_name,
            base_url=project_url,
            owner=current_user
        )
        try:
            db.session.add(new_project)
            db.session.commit()
            flash('Project created successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating project: {e}', 'danger')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/project/<int:project_id>/run_audit')
@login_required
def run_audit(project_id):
    from auditor_pro.tasks import run_audit_task
    project = Project.query.get_or_404(project_id)
    if project.owner != current_user:
        flash('You do not have permission to audit this project.', 'danger')
        return redirect(url_for('main.dashboard'))
    try:
        new_report = AuditReport(
            project_id=project.id,
            status='PENDING'
        )
        db.session.add(new_report)
        db.session.commit()
        run_audit_task.delay(new_report.id, project.base_url)

        socketio.emit(
            'audit_started',
            {'project_id': project.id},
            room=f'user_{current_user.id}'
        )

    except Exception as e:
        db.session.rollback()
        flash(f"Error queuing audit: {e}", 'danger')

    return redirect(url_for('main.dashboard'))


@main_bp.route('/project/<int:project_id>')
@login_required
def view_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.owner != current_user:
        abort(403)

    all_reports = project.reports.filter_by(status='COMPLETE')\
                                 .order_by(AuditReport.created_at.asc())\
                                 .all()

    chart_data = {
        'labels': [r.created_at.strftime('%b %d') for r in all_reports],
        'overall': [r.overall_score for r in all_reports],
        'performance': [r.performance_score for r in all_reports],
        'accessibility': [r.a11y_score for r in all_reports],
        'seo': [r.seo_score for r in all_reports],
    }

    latest_report = all_reports[-1] if all_reports else None

    return render_template(
        'project_detail.html',
        project=project,
        report=latest_report,
        all_reports=reversed(all_reports),
        chart_data=json.dumps(chart_data)
    )

@main_bp.route('/report/<int:report_id>/pdf')
@login_required
def download_pdf_report(report_id):
    from weasyprint import HTML

    report = AuditReport.query.get_or_404(report_id)
    project = report.project
    if project.owner != current_user:
        abort(403)
    if report.status != 'COMPLETE':
        flash('Cannot generate PDF for an incomplete audit.', 'danger')
        return redirect(url_for('main.view_project', project_id=project.id))
    css_url = url_for('static', filename='css/style.css', _external=True)
    html_string = render_template(
        'report_pdf.html',
        report=report,
        project=project,
        css_url=css_url
    )
    pdf = HTML(string=html_string, base_url=request.base_url).write_pdf()
    filename = f"{project.name.replace(' ', '_')}_Report_{report.created_at.strftime('%Y-%m-%d')}.pdf"
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment;filename={filename}"
        }
    )

@main_bp.route('/project/<int:project_id>/set_schedule', methods=['POST'])
@login_required
def set_schedule(project_id):
    project = Project.query.get_or_404(project_id)
    if project.owner != current_user:
        abort(403)
    schedule = request.form.get('schedule')
    if schedule not in ['none', 'daily', 'weekly']:
        flash('Invalid schedule selected.', 'danger')
        return redirect(url_for('main.dashboard'))
    try:
        project.schedule = schedule
        db.session.commit()
        flash(f'Audit schedule for "{project.name}" updated to {schedule}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating schedule: {e}', 'danger')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/project/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.owner != current_user:
        abort(403)
    try:
        db.session.delete(project)
        db.session.commit()
        flash(f'Project "{project.name}" has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting project: {e}', 'danger')
    return redirect(url_for('main.dashboard'))


@socketio.on('join_room')
def handle_join_room_event(data):
    """
    Handles a client's request to join a private room.
    """
    if not current_user.is_authenticated:
        return
    room = data.get('room')
    if room == f'user_{current_user.id}':
        print(f"WEBSOCKET: Client {current_user.email} joining room: {room}")
        join_room(room)
    else:
        print(f"WEBSOCKET: Unauthorized room join attempt: {room} by {current_user.email}")


@main_bp.app_errorhandler(404)
def page_not_found(e):
    """
    Renders the custom 404 error page.
    """
    return render_template('errors/404.html'), 404

@main_bp.app_errorhandler(500)
def internal_server_error(e):
    """
    Renders the custom 500 error page.
    """
    return render_template('errors/500.html'), 500

@main_bp.app_errorhandler(403)
def forbidden(e):
    """
    Renders a custom 403 (forbidden) error page.
    """
    return render_template('errors/404.html'), 403