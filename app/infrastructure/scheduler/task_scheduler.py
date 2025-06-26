"""
Provides task scheduling functionality using threads.
"""

import threading
import time
from collections.abc import Callable
from typing import Any

import schedule


class AppScheduler:
    """
    Class for scheduling tasks using the schedule library.

    Attributes:
        _scheduler (schedule): The instance of the schedule library.
        _scheduler_thread (threading.Thread | None): The thread that runs the
            scheduler.
        _stop_event (threading.Event): An event used to stop the scheduler.

    Methods:
        start(): Starts the scheduler thread if it is not already running.
        stop(): Stops the scheduler thread and waits for it to finish.
        schedule_task(task_func, tag, schedule_time, day_of_week=None,
            cancel_existing=False, **kwargs):
                Schedules a task to run at a specified time.
        get_all_jobs(): Returns a list of dictionaries containing information
            about all scheduled jobs.
        clear_jobs(tag=None): Clears all scheduled jobs or those with a
            specific tag.
    """

    def __init__(self) -> None:
        """
        Initializes the scheduler.
        """
        self._scheduler = schedule
        self._scheduler_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def _run_pending_jobs(self) -> None:
        """Runs pending jobs in the scheduler.

        Args:
            self (Scheduler): The instance of the Scheduler class.

        Returns:
            None
        """

        while not self._stop_event.is_set():
            self._scheduler.run_pending()
            time.sleep(1)

    def start(self) -> None:
        """Start the scheduler thread if it is not already running.

        Args:
            self (Scheduler): The instance of the Scheduler class.

        Returns:
            None
        """

        if (
            self._scheduler_thread is None
            or not self._scheduler_thread.is_alive()
        ):
            self._scheduler_thread = threading.Thread(
                target=self._run_pending_jobs, daemon=True
            )
            self._scheduler_thread.start()

    def stop(self) -> None:
        """
        Stops the scheduler thread and waits for it to finish.

        Args:
            self (Scheduler): The instance of the Scheduler class.

        Returns:
            None
        """

        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._stop_event.set()
            self._scheduler_thread.join()
            self._stop_event.clear()

    def schedule_task(
        self,
        task_func: Callable,
        tag: str,
        schedule_time: str,
        day_of_week: str | None = None,
        cancel_existing: bool = False,
        **kwargs: dict,
    ) -> None:
        """Schedule a task to run at a specified time.

        Args:
            task_func (Callable): The function to be scheduled.
            tag (str): A unique identifier for the task.
            schedule_time (str): The time of day to run the task.
            day_of_week (str | None, optional): The day of the week to run the
                task. Defaults to None.
            cancel_existing (bool, optional): Whether to cancel any existing
                scheduled tasks with the same tag. Defaults to False.
            **kwargs: Additional keyword arguments to be passed to
                the task function.

        Returns:
            None
        """

        if cancel_existing:
            self._scheduler.clear()
        job_builder = self._scheduler.every()
        if day_of_week:
            if day_of_week.lower() == "sunday":
                job_builder = job_builder.sunday
            elif day_of_week.lower() == "monday":
                job_builder = job_builder.monday
            elif day_of_week.lower() == "tuesday":
                job_builder = job_builder.tuesday
            elif day_of_week.lower() == "wednesday":
                job_builder = job_builder.wednesday
            elif day_of_week.lower() == "thursday":
                job_builder = job_builder.thursday
            elif day_of_week.lower() == "friday":
                job_builder = job_builder.friday
            elif day_of_week.lower() == "saturday":
                job_builder = job_builder.saturday
            job_builder.at(schedule_time).do(task_func, **kwargs).tag(tag)
        else:
            job_builder.day.at(schedule_time).do(task_func, **kwargs).tag(tag)

    def get_all_jobs(self) -> list[dict[str, Any]]:
        """
        Returns a list of dictionaries containing information about all
        scheduled jobs.

        Returns:
            list[dict[str, Any]]: A list of dictionaries, where each dictionary
                contains information about a scheduled job.

            The keys in the dictionary are:
                tag (str): The tags associated with the job.
                task (str): The function or method that is scheduled to run.
                last_run (datetime): The time when the job was last run.
                next_run (datetime): The time when the job will next run.
                unit (str): The time unit for the job's interval.
                interval (int): The number of units between each run of the
                    job.
                period (int): The number of times the job has been run.

        """

        jobs_info = []
        for job in self._scheduler.get_jobs():
            jobs_info.append(
                {
                    "tag": job.tags,
                    "task": str(job.job_func),
                    "last_run": job.last_run,
                    "next_run": job.next_run,
                    "unit": job.unit,
                    "interval": job.interval,
                    "period": job.period,
                }
            )
        return jobs_info

    def clear_jobs(self, tag: str | None = None) -> None:
        """Clears all scheduled jobs or those with a specific tag.

        Args:
            tag (str | None): The tag to identify the jobs to clear.
                If None, clears all scheduled jobs. Defaults to None.

        Returns:
            None
        """

        if tag:
            self._scheduler.clear(tag)
        else:
            self._scheduler.clear()
