"""
Handles API endpoints and related logic for managing tasks within
the application.
"""

import threading
from collections.abc import Callable

from flask import (
    Blueprint,
    Response,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from app.application.dtos import ScheduleTaskDTO, TaskRunRequestDTO
from app.application.services.task_service import TaskService
from app.application.use_cases.deploy_lpar_task import DeployLparTaskUseCase
from app.application.use_cases.schedule_lpar_task import (
    ScheduleLparTaskUseCase,
)


def create_task_blueprint(
    task_service: TaskService,
    deploy_lpar_task_use_case: DeployLparTaskUseCase,
    schedule_lpar_task_use_case: ScheduleLparTaskUseCase,
    socketio_emit: Callable,  # Inject socketio.emit
) -> Blueprint:
    """Create a blueprint for handling task-related routes.

    Args:
        task_service (TaskService): An instance of the TaskService class.
        deploy_lpar_task_use_case (DeployLparTaskUseCase): An instance of
            the DeployLparTaskUseCase class.
        schedule_lpar_task_use_case (ScheduleLparTaskUseCase): An instance of
            the ScheduleLparTaskUseCase class.
        socketio_emit (Callable): A function that emits a message using
            SocketIO.

    Returns:
        Blueprint: The created blueprint for handling task-related routes.
    """

    task_bp = Blueprint("task_bp", __name__)

    @task_bp.route("/lpar/tasks", methods=["GET"])
    @login_required
    def lpar_tasks() -> str:
        """
        Run a task on one or more LPARs.

        Parameters:
        - id (int, optional): The ID of the LPAR to run the task on.
            If not provided, the function will expect a list of LPAR IDs in
            the form data parameter "identifier[]".

        Returns:
        - str: The name of the HTML template to render.
        """

        lpars = task_service.lpar_repo.find(
            task_service.lpar_repo.model, criteria={"enable": 1}
        )
        return render_template("lpar_tasks.html", results=lpars)

    @task_bp.route("/lpar/tasks/run", methods=["POST"])
    @task_bp.route("/lpar/tasks/run/<int:id>", methods=["GET"])
    @login_required
    def lpar_tasks_run(id: int | None = None) -> Response | str:
        """
        Run a task on one or more LPARs.

        Parameters:
        - id (int, optional): The ID of the LPAR to run the task on.
            If not provided, the function will expect a list of LPAR IDs in
            the form data parameter "identifier[]".

        Returns:
        - str: The name of the HTML template to render.
        """

        if request.method == "POST":
            identifiers = tuple(map(int, request.form.getlist("identifier[]")))
        elif request.method == "GET" and id is not None:
            identifiers = (id,)
        else:
            return redirect(url_for("task_bp.lpar_tasks"))
        task_run_dto = TaskRunRequestDTO(lpar_ids=list(identifiers))
        threading.Thread(
            target=deploy_lpar_task_use_case.execute,
            args=(task_run_dto, socketio_emit),
        ).start()
        return render_template("lpar_tasks_run.html")

    @task_bp.route("/scheduler/list", methods=["GET"])
    @login_required
    def scheduler_list() -> list:
        """
        Returns a list of scheduled tasks.

        Args:
            None

        Returns:
            List[dict]: A list of dictionaries containing information about
                each scheduled task.
        """

        schedules_result = task_service.get_scheduled_tasks()
        return render_template("scheduler_list.html", results=schedules_result)

    @task_bp.route("/scheduler/set", methods=["POST"])
    @login_required
    def set_scheduler() -> Response:
        """
        Set a scheduler task for a Logical Partition (LPAR).

        Parameters:
        - lpar_id (int): The ID of the LPAR to schedule.
        - schedule_time (str): The time when the task should be executed.
        - day_of_week (str, optional): The day of the week when the task
            should be executed.
        - cancel_jobs (bool, optional): Whether to cancel any existing jobs
            for the LPAR.

        Returns:
        - None
        """

        lpar_id = int(request.form["lpar_id"])
        schedule_time = request.form["schedule_time"]
        day_of_week = request.form.get("day_of_week")  # Optional
        schedule_dto = ScheduleTaskDTO(
            lpar_id=lpar_id,
            schedule_time=schedule_time,
            day_of_week=day_of_week,
            cancel_jobs=request.form.get("cancel_jobs")
            == "true",  # Check if checkbox is ticked
        )
        schedule_lpar_task_use_case.execute(schedule_dto)
        flash("Task scheduled successfully!", "success")
        return redirect(
            url_for("lpar_bp.lpar_settings")
        )  # Redirect back to LPAR settings or similar

    @task_bp.route("/scheduler/clear/<string:tag>", methods=["GET"])
    @login_required
    def clear_scheduler_tag(tag: str) -> Response:
        """Clears all scheduled tasks with a given tag.

        Args:
            tag (str): The tag to identify the scheduled tasks to clear.

        Returns:
            None
        """

        task_service.clear_scheduled_tasks(tag=tag)
        flash(f"Scheduled tasks with tag '{tag}' cleared.", "info")
        return redirect(url_for("task_bp.scheduler_list"))

    @task_bp.route("/scheduler/clear_all", methods=["GET"])
    @login_required
    def clear_all_schedulers() -> Response:
        """Clears all scheduled tasks in the system.

        Args:
            None

        Returns:
            Redirect to the scheduler list page.
        """

        task_service.clear_scheduled_tasks(tag=None)
        flash("All scheduled tasks cleared.", "info")
        return redirect(url_for("task_bp.scheduler_list"))

    return task_bp
