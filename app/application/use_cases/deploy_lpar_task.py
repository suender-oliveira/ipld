"""
Implements use case for deploying LPAR tasks.
"""

from collections.abc import Callable

from app.application.dtos import TaskRunRequestDTO
from app.application.services.task_service import TaskService


class DeployLparTaskUseCase:
    """
    Class that executes a task to run deploy tasks on LPARs.
    """

    def __init__(self, task_service: TaskService) -> None:
        """
        Initializes the use case with a given task service.

        Parameters:
            - task_service (TaskService): The task service to use for executing
                the deploy tasks.

        Returns:
            None
        """

        self.task_service = task_service

    def execute(
        self, dto: TaskRunRequestDTO, socketio_emitter: Callable
    ) -> None:
        """
        Executes a task to run deploy tasks on LPARs.

        Parameters:
            - dto (TaskRunRequestDTO): The DTO containing the LPAR IDs to
                run deploy tasks for.
            - socketio_emitter (Callable): A function that emits events using
                Socket.IO.

        Returns:
            None
        """

        # Inject the emitter into the service before execution
        self.task_service.set_socketio_emitter(socketio_emitter)

        self.task_service.run_deploy_tasks(dto.lpar_ids)
