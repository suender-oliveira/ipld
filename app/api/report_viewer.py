"""
Handles API endpoints and related logic for generating and viewing reports
within the application.
"""

import datetime
import os

import flask
import werkzeug
from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import login_required

from app.application.dtos import ReportFilterDTO
from app.application.services.report_service import ReportService
from app.infrastructure.config.settings import app_settings


def create_report_blueprint(report_service: ReportService) -> Blueprint:
    """Creates a blueprint for handling LPAR report routes.

    Args:
        report_service (ReportService): An instance of the ReportService class.

    Returns:
        Blueprint: A Flask blueprint object for the LPAR reports route.
    """

    report_bp = Blueprint("report_bp", __name__)

    @report_bp.route("/lpar/reports", methods=["GET"])
    @login_required
    def lpar_results_show_dir() -> str:
        """Shows the results directory for the current user.

        Returns:
            str: The rendered HTML template for the LPAR results directory.
        """

        try:
            files = os.listdir(app_settings.ROOT_RESULTS)
        except FileNotFoundError:
            files = []
            flash(
                "Results directory not found. Please run a deployment first.",
                "info",
            )
        except OSError as e:
            files = []
            flash(f"Error accessing results directory: {e}", "danger")
        return render_template(
            "lpar_results.html",
            files=files,
            dir_path="",  # Root path
            os=os,  # Pass os module for path manipulation in template (e.g., isdir, isfile)
            root_dir=app_settings.ROOT_RESULTS,
        )

    @report_bp.route("/lpar/reports/<path:dir_path>", methods=["GET"])
    @login_required
    def lpar_results_show_dir_dynamic(dir_path: str = "") -> str:
        """Show the results directory.

        Args:
            dir_path (str): The path to the directory to show. Defaults to
                the root results directory.

        Returns:
            render_template: The rendered template with the list of files and
                directory path.
        """

        safe_base_path = os.path.abspath(app_settings.ROOT_RESULTS)
        requested_path = os.path.abspath(
            os.path.join(safe_base_path, dir_path)
        )

        if not requested_path.startswith(safe_base_path):
            abort(403, description="Access denied.")
        if not os.path.isdir(requested_path):
            abort(404, description="Not found")
        try:
            files = os.listdir(requested_path)
        except OSError as error:
            abort(500, description=f"Error accessing the directory: {error}")
        return render_template(
            "lpar_results.html",
            files=files,
            dir_path=dir_path,
            os=os,
            root_dir=app_settings.ROOT_RESULTS,
        )

    @report_bp.route(
        "/lpar/reports/download/<path:file_path>", methods=["GET"]
    )
    @login_required
    def lpar_results_download_file(
        file_path: str,
    ) -> flask.wrappers.Response | werkzeug.wrappers.response.Response:
        """Download a file from the LPAR results directory.

        Args:
            file_path (str): The path to the file relative to the root of
                the LPAR results directory.

        Returns:
            flask.Response: The response object containing the file to be
                downloaded.

        Raises:
            FileNotFoundError: If the specified file does not exist in
                the LPAR results directory.
        """

        full_file_path = os.path.join(app_settings.ROOT_RESULTS, file_path)
        if os.path.isfile(full_file_path):
            return send_from_directory(app_settings.ROOT_RESULTS, file_path)
        flash("Error: File not found", "danger")
        return redirect(url_for("report_bp.lpar_results_show_dir"))

    @report_bp.route("/lpar/results/<string:view>", methods=["GET"])
    @login_required
    def lpar_results_table(view: str) -> str:
        """
        Generate a table of LPAR results based on the specified view.

        Parameters:
        - view (str): The type of view to render. Must be one of "done",
            "fail", or "last_ipl".

        Returns:
        - str: The rendered HTML template for the LPAR results table.
        """

        report_filter_dto = ReportFilterDTO(view_type=view)
        results = report_service.get_ipl_reports(report_filter_dto)

        template_map = {
            "done": "lpar_results_table.html",
            "fail": "lpar_results_table_fail.html",
            "last_ipl": "lpar_results_table_last_ipl.html",
        }
        template_name = template_map.get(view, "lpar_results_table.html")
        return render_template(
            template_name,
            datetime=datetime,
            results=results,
        )

    @report_bp.route("/system/database/import", methods=["GET", "POST"])
    @report_bp.route(
        "/system/database/import/<string:action>", methods=["GET", "POST"]
    )
    @login_required
    def import_database(action: str | None = None) -> str | Response:
        """Imports data into a database table.

        Args:
            action (str, optional): The action to perform. Defaults to None.

        Returns:
            flask.Response: The rendered HTML template or a redirect response.
        """

        if request.method == "GET":
            return render_template("system_database_import.html")
        if request.method == "POST" and action == "add":
            import json

            try:
                table_name = request.form["table"]
                data_to_import_str = request.form["data_to_import"]

                _data_list = json.loads(data_to_import_str)
                flash(
                    f"Import to table '{table_name}' "
                    "initiated (logic placeholder).",
                    "info",
                )
                return redirect(url_for("report_bp.import_database"))
            except json.JSONDecodeError:
                flash("Invalid JSON data provided.", "danger")
            except Exception as e:
                flash(f"An error occurred during import: {e}", "danger")
            return render_template("system_database_import.html")
        flash("Invalid import action.", "danger")
        return redirect(url_for("report_bp.import_database"))

    return report_bp
