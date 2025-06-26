"""
Implements use case for scheduling LPAR tasks.
"""

from app.application.dtos import ScheduleTaskDTO
from app.application.services.task_service import TaskService


class ScheduleLparTaskUseCase:
    """
    Use case to schedule a task to run on a specific LPAR.
    """

    def __init__(self, task_service: TaskService) -> None:
        """
        Initializes the use case with the given task service.

        Args:
            task_service (TaskService): The task service to use for
                scheduling tasks.

        Returns:
            None
        """

        self.task_service = task_service

    def execute(self, dto: ScheduleTaskDTO) -> None:
        self.task_service.schedule_lpar_task(dto)
