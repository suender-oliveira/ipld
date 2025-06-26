"""
Contains API endpoints for managing LPAR settings and related functionalities.
"""

from collections.abc import Callable

from flask import (
    Blueprint,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from app.application.dtos import DryRunRequestDTO, LparCreateDTO, LparUpdateDTO
from app.application.services.lpar_service import LparService
from app.application.use_cases.dry_run_check import DryRunCheckUseCase


def create_lpar_blueprint(
    lpar_service: LparService,
    dry_run_use_case: DryRunCheckUseCase,
    socketio_emit: Callable,
) -> Blueprint:
    """Create a blueprint for managing LPAR settings.

    Args:
        lpar_service (LparService): An instance of the LparService class.
        dry_run_use_case (DryRunCheckUseCase): An instance of
            the DryRunCheckUseCase class.
        socketio_emit (Callable): A function that emits a message using
            SocketIO.

    Returns:
        Blueprint: The created blueprint for managing LPAR settings.
    """

    lpar_bp = Blueprint("lpar_bp", __name__)

    @lpar_bp.route("/lpar/settings", methods=["GET"])
    @login_required
    def lpar_settings() -> str:
        """
        Retrieve all LPAR settings from the system and render them in
            a template.

        Returns:
            Rendered HTML template displaying the LPAR settings.
        """

        lpars = lpar_service.get_all_lpars()
        return render_template("lpar_settings.html", results=lpars)

    @lpar_bp.route("/lpar/settings/new/step-1", methods=["GET"])
    @login_required
    def lpar_settings_new() -> list:
        """
        Returns a list of all existing LPARs in the system.

        Parameters:
        None

        Returns:
        A list of dictionaries containing information about each LPAR,
            including its name, UUID, and other attributes.
        """
        lpars = lpar_service.get_all_lpars()
        return render_template("lpar_settings_new.html", results=lpars)

    @lpar_bp.route("/lpar/settings/new/step-2", methods=["POST"])
    @login_required
    async def lpar_settings_new_step2() -> str:
        """
        Handles the second step of the LPAR settings creation process.

        Parameters:
        - hostname (str): The hostname of the system where the LPAR will
            be created.
        - username (str): The username of the user who will own the LPAR.
        - dataset (str): The name of the dataset that will be used for
            the LPAR.
        - lpar_name (str): The name of the LPAR to be created.

        Returns:
        - str: The HTML template to render for the second step of
            the LPAR settings creation process.
        """

        hostname = request.form["hostname"]
        username = request.form["user_id"]
        dataset = request.form["dataset"]
        lpar_name = request.form["lpar"]
        dry_run_dto = DryRunRequestDTO(
            hostname=hostname, username=username, dataset=dataset
        )

        # Execute dry run asynchronously in a separate thread,
        # and pass the socketio_emit function for updates.
        dry_run_use_case.execute(dry_run_dto, socketio_emit)
        field_list = {
            "lpar": lpar_name,
            "hostname": hostname,
            "dataset": dataset,
            "user_id": username,
        }
        return render_template(
            "lpar_settings_new_step2.html", results=field_list
        )

    @lpar_bp.route("/lpar/settings/dry-run", methods=["POST"])
    @login_required
    async def lpar_settings_dry_run_api() -> tuple[Response, int]:
        """
        Execute a dry run of LPAR settings on a given hostname.

        Args:
            hostname (str): The hostname of the system to run the dry run on.
            username (str): The username of the user running the dry run.
            dataset (str): The name of the dataset to use for the dry run.

        Returns:
            tuple[Response, int]: A tuple containing a Flask response object
                and an HTTP status code.
        """

        hostname = request.form["hostname"]
        username = request.form["user_id"]
        dataset = request.form["dataset"]
        dry_run_dto = DryRunRequestDTO(
            hostname=hostname, username=username, dataset=dataset
        )
        # Execute dry run asynchronously in a separate thread,
        # and pass the socketio_emit function for updates.
        dry_run_use_case.execute(dry_run_dto, socketio_emit)
        return jsonify({"status": "Dry run initiated"}), 202

    @lpar_bp.route("/lpar/settings/new", methods=["POST"])
    @login_required
    def lpar_settings_insert() -> Response:
        """Insert a new LPAR settings into the database.

        Args:
            lpar (str): The name of the LPAR.
            hostname (str): The hostname of the LPAR.
            dataset (str): The dataset to use for the LPAR.
            username (str): The username of the user creating the LPAR.

        Returns:
            Response: A Flask response object.
        """

        lpar_name = request.form["lpar"]
        hostname = request.form["hostname"]
        dataset = request.form["dataset"]
        username = request.form["user_id"]
        create_dto = LparCreateDTO(
            lpar=lpar_name,
            hostname=hostname,
            dataset=dataset,
            username=username,
        )
        new_lpar = lpar_service.create_lpar(create_dto)
        if new_lpar:
            flash(
                f"The LPAR {new_lpar.lpar} was created successfully.",
                "success",
            )
        else:
            flash(
                f"The LPAR {lpar_name} already exists or an error occurred.",
                "danger",
            )
        return redirect(url_for("lpar_bp.lpar_settings"))

    @lpar_bp.route("/lpar/settings/<int:id>", methods=["GET"])
    @login_required
    def lpar_settings_detail(id: int) -> Response | str:
        """
        Retrieve LPAR settings details.

        Parameters:
        - id (int): The ID of the LPAR to retrieve settings for.

        Returns:
        - Response: If the LPAR is not found, a flash message is displayed
            and the user is redirected to the LPAR settings page.
        - str: If the LPAR is found, the LPAR details are rendered in
            the lpar_settings_detail.html template.
        """

        lpar = lpar_service.get_lpar_by_id(id)
        if not lpar:
            flash("LPAR not found.", "danger")
            return redirect(url_for("lpar_bp.lpar_settings"))
        return render_template("lpar_settings_detail.html", results=[lpar])

    @lpar_bp.route("/lpar/settings/update/<int:id>", methods=["POST"])
    @login_required
    def lpar_settings_update(id: int) -> Response:
        """
        Update LPAR settings.

        Args:
            id (int): The ID of the LPAR to update.
            lpar (str): The new LPAR name.
            hostname (str): The new hostname for the LPAR.
            dataset (str): The new dataset for the LPAR.
            username (str): The new username for the LPAR.
            enabled (int): Whether the LPAR is enabled or disabled.
            schedule (str): The new schedule for the LPAR.

        Returns:
            Response: A response object containing the updated
                LPAR information.
        """

        update_dto = LparUpdateDTO(
            id=id,
            lpar=request.form["lpar"],
            hostname=request.form["hostname"],
            dataset=request.form["dataset"],
            username=request.form["username"],
            enabled=int(request.form["enabled"]),
            schedule=request.form["schedule"],
        )
        updated_lpar = lpar_service.update_lpar(update_dto)
        if updated_lpar:
            flash(
                f"The LPAR {updated_lpar.lpar} configuration has been "
                "updated successfully.",
                "success",
            )
        else:
            flash(f"An error occurred while updating LPAR ID {id}.", "danger")
        return redirect(url_for("lpar_bp.lpar_settings_detail", id=id))

    return lpar_bp
