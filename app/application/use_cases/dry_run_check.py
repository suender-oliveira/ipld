"""
Implements use case for performing dry run checks on LPARs
"""

from collections.abc import Callable

from app.application.dtos import DryRunRequestDTO
from app.application.services.task_service import TaskService


class DryRunCheckUseCase:
    """
    Class responsible for executing dry runs based on provided request data.
    """

    def __init__(self, task_service: TaskService) -> None:
        """
        Initializes the class with a reference to the task service.

        Parameters:
        - task_service (TaskService): The task service instance to use.

        Returns:
        None
        """

        self.task_service = task_service

    def execute(
        self, dto: DryRunRequestDTO, socketio_emitter: Callable
    ) -> None:
        """
        Executes a dry run based on the provided request data.

        Parameters:
        - dto (DryRunRequestDTO): The request data for the dry run.
        - socketio_emitter (Callable): A function that emits events to
            the client using Socket.IO.

        Returns:
        None
        """

        # Inject the emitter into the service before execution
        self.task_service.set_socketio_emitter(socketio_emitter)

        self.task_service.run_dry_run(dto)
