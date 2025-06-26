"""
Responsible for managing LPAR deployments, scheduling tasks, handling dry runs,
and interacting with various services.
"""

import asyncio
import concurrent.futures
import logging
import os
import shutil
from collections.abc import Callable
from typing import Any

from app.application.dtos import (
    DryRunRequestDTO,
    DryRunStatusDTO,
    ScheduleTaskDTO,
    TaskProgressDTO,
)
from app.domain.repositories import ILparRepository
from app.domain.services import (
    IDryRunExternalService,
    IExternalSSHService,
    ISchedulerService,
)
from app.infrastructure.config.settings import app_settings
from app.infrastructure.external_apis.cirrus_client import CirrusClient

logger = logging.getLogger(__name__)


class TaskService:
    """
    Providing methods for deploying, scheduling, performing dry runs,
    retrieving scheduled tasks, and clearing scheduled tasks.
    """

    def __init__(
        self,
        lpar_repo: ILparRepository,
        ssh_service: IExternalSSHService,
        dryrun_ssh_service: IDryRunExternalService,
        scheduler_service: ISchedulerService,
        cirrus_client: CirrusClient,
    ) -> None:
        """
        Initializes the TaskService with dependencies.

        Args:
            lpar_repo (ILparRepository): The repository for interacting
                with LPAR data.
            ssh_service (IExternalSSHService): Service for
                handling SSH connections.
            dryrun_ssh_service (IDryRunExternalService): Service for
                performing
                dry run checks via SSH.
            scheduler_service (ISchedulerService): Service for scheduling
                tasks.
            cirrus_client (CirrusClient): Client for interacting with
                Cirrus API.

        Returns:
            None
        """

        self.lpar_repo = lpar_repo
        self.ssh_service = ssh_service
        self.dryrun_ssh_service = dryrun_ssh_service
        self.scheduler_service = scheduler_service
        self.cirrus_client = cirrus_client
        self.socketio_emitter: Callable | None

    def set_socketio_emitter(self, emitter_func: Callable) -> None:
        """Sets the socket.io emitter function.

        Args:
            emitter_func (Callable): The socket.io emitter function to set.

        Returns:
            None
        """

        self.socketio_emitter = emitter_func

    async def _deploy_lpar_loop(
        self, lpar_hostname: str, username: str, qualifier: str
    ) -> str:
        """
        Deploy the LPAR loop on a remote server.

        Parameters:
            lpar_hostname (str): The hostname of the LPAR to deploy
                the loop on.
            username (str): The username to use for SSH access to the LPAR.
            qualifier (str): The qualifier to use for the deployment.

        Returns:
            str: A string indicating the status of the deployment,
                either "SUCCESS" or "ERROR".
        """

        local_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "../../.."
        )
        lpar_name_prefix = lpar_hostname.split(".")[0]
        remote_tmp_path = f"{app_settings.ROOT_TMP_ANALYSIS}{lpar_name_prefix}"
        local_results_path = os.path.join(
            local_dir, app_settings.ROOT_RESULTS, lpar_name_prefix
        )

        logger.info(f"Starting deploy loop for {lpar_hostname}")

        # 1. Prepare the remote temporary space
        prepare_command = (
            f"if [[ -d {remote_tmp_path} ]]; then"
            f"rm -rf {remote_tmp_path} && "
            f"mkdir -p {remote_tmp_path}; fi;"
            f"ls -la {remote_tmp_path}"
        )

        try:
            check_space_output = await self.ssh_service.run_command(
                lpar_hostname, username, prepare_command
            )
            logger.debug(
                f"Remote space preparation output: {check_space_output}"
            )
        except Exception:
            logger.exception(
                f"Failed to prepare remote space on {lpar_hostname}"
            )
            return "ERROR: An error occured on prepare the remote file space"

        # 2. Upload the script files
        files_to_load = [
            "ipld_calc.awk",
            "ipld_parsing.awk",
            "patterns",
            "main.sh",
            "methods.sh",
        ]
        script_dir = os.path.join(local_dir, "scripts")

        for file_to_load in files_to_load:
            local_file_path = os.path.join(script_dir, file_to_load)

            try:
                await self.ssh_service.upload_file(
                    lpar_hostname, username, local_file_path, remote_tmp_path
                )
                logger.debug(
                    f"Uploaded {file_to_load} to "
                    f"  {lpar_hostname}:{remote_tmp_path}"
                )
            except Exception:
                logger.exception(
                    f"Failed to upload {file_to_load} to {lpar_hostname}"
                )
                return (
                    "ERROR: An error occured on upload"
                    f"file {file_to_load.upper()} to {lpar_hostname}"
                )

        # 3. Execute main.sh on the remote server
        execute_command = (
            f"{remote_tmp_path}/main.sh -r cli "
            f"-a {lpar_hostname} -q {qualifier}"
        )

        try:
            execution_output = await self.ssh_service.run_command(
                lpar_hostname, username, execute_command
            )
            logger.info(
                f"main.sh execution output for {lpar_hostname}: "
                f"{execution_output[:200]}..."
            )
        except Exception:
            logger.exception(f"Failed to execute main.sh on {lpar_hostname}")
            return "ERROR: An error occured running the main.sh"

        # 4. Donwload CSV file results
        os.makedirs(local_results_path, exist_ok=True)
        if os.path.isdir(local_results_path):
            shutil.rmtree(local_results_path)
        os.makedirs(local_results_path)

        remote_csv_path = f"{remote_tmp_path}/*.CSV"

        try:
            await self.ssh_service.download_file(
                lpar_hostname, username, remote_csv_path, local_results_path
            )
            logger.info(
                f"Downloaded CSV results from {lpar_hostname} "
                f"to {local_results_path}"
            )
        except Exception:
            logger.exception(
                f"Failed to download CSV results from {lpar_hostname}"
            )
            return "ERROR: An error occured downloading CSV results"

        # 5. Clean up remote temporary space
        cleanup_command = (
            f"if [[ -d {remote_tmp_path} ]]; then"
            f"rm -rf {remote_tmp_path}; fi; "
            f"if [[ -d {app_settings.ROOT_TMP_ANALYSIS} ]]; then "
            f"rm -rf {app_settings.ROOT_TMP_ANALYSIS}; fi"
        )

        try:
            await self.ssh_service.run_command(
                lpar_hostname, username, cleanup_command
            )
            logger.info(f"Cleaned up remote space on {lpar_hostname}")
        except Exception:
            logger.exception(
                f"Failed to clean up remote space on {lpar_hostname}"
            )
            return f"ERROR: An cleaning up remote space on {lpar_hostname}"

        return lpar_hostname

    def run_deploy_tasks(self, lpar_ids: list[int]) -> None:
        """
        Deploy LPARs on the system.

        Args:
            lpar_ids (list[int]): A list of IDs of LPARs to deploy.

        Returns:
            None
        """

        lpars_to_deploy = self.lpar_repo.find(
            self.lpar_repo.model, in_values={"id": lpar_ids}
        )

        if not lpars_to_deploy and self.socketio_emitter:
            self.socketio_emitter(
                "task_progress",
                TaskProgressDTO(
                    result=[],
                    percent=100,
                    error="No LPARs found for given IDs",
                ).__dict__,
            )
            return

        lpar_status = {lpar.hostname: "wait" for lpar in lpars_to_deploy}

        if self.socketio_emitter:
            self.socketio_emitter(
                "task_progress",
                TaskProgressDTO(
                    result=[f"'{h}': '{s}'" for h, s in lpar_status.items()],
                    percent=10,
                    error=None,
                ).__dict__,
            )

        with (
            concurrent.futures,
            concurrent.futures.ThreadPoolExecutor(
                max_workers=app_settings.THREAD_WORKS
            ) as executor,
        ):
            futures = {
                executor.submit(
                    asyncio.run,
                    self._deploy_lpar_loop(
                        lpar.hostname, lpar.username, lpar.dataset
                    ),
                ): lpar.hostname
                for lpar in lpars_to_deploy
            }

            completed_count = 0
            total_tasks = len(futures)
            errors = []

            for future in concurrent.futures.concurrent.futures.as_completed(
                futures
            ):
                hostname = futures[future]

                try:
                    result = future.result()
                    if result.startswith("ERROR"):
                        lpar_status[hostname] = "error"
                        errors.append(
                            f"Deployment failed for {hostname}: {result}"
                        )
                        logger.error(
                            f"Deployment failed for {hostname}: {result}"
                        )
                    else:
                        lpar_status[hostname] = "done"
                        logger.info(f"Deployment successful for {hostname}")
                except Exception as e:
                    lpar_status[hostname] = "error"
                    errors.append(
                        f"Deployment failed for {hostname} with exception: {e}"
                    )
                    logger.exception(f"Deployment failed for {hostname}")

                completed_count += 1
                percent = (completed_count / total_tasks) * 100

                if self.socketio_emitter:
                    self.socketio_emitter(
                        "task_progress",
                        TaskProgressDTO(
                            result=[
                                f"'{h}': '{s}'" for h, s in lpar_status.items()
                            ],
                            percent=percent,
                            error=", ".join(errors) if errors else None,
                        ).__dict__,
                    )

                logger.info("All deployments tasks completed")

    async def _perform_dry_run_checks(
        self, hostname: str, username: str, dataset: str
    ) -> None:
        """Performs dry run checks on a given hostname.

        Args:
            hostname (str): The hostname to check.
            username (str): The username to use for SSH connection.
            dataset (str): The name of the dataset to check.

        Returns:
            None
        """

        status = DryRunStatusDTO()
        if self.socketio_emitter:
            self.socketio_emitter("dry_run", status.__dict__)

        try:
            # 1. Check Egress Firewall Rules
            firewall_ok = self.cirrus_client.check_egress_firewall(hostname)
            status.firewall_rules = "done" if firewall_ok else "error"

            if self.socketio_emitter:
                self.socketio_emitter("dry_run", status.__dict__)

            if not firewall_ok:
                logger.warning(
                    f"Dry run failed: Firewall rule is missing for {hostname}"
                )
                return

            # 2. Check SSH connection and Dataset /tmp space
            ssh_checks_result = (
                await self.dryrun_ssh_service.check_ssh_connection(
                    hostname, username, dataset
                )
            )

            if ssh_checks_result.get("check_ssh_login") == username:
                status.check_ssh_login = "done"
            else:
                status.check_ssh_login = "error"

            if int(ssh_checks_result.get("check_dataset_access", 0)) > 1:
                status.check_dataset_access = "done"
            else:
                status.check_dataset_access = "error"

            if int(ssh_checks_result.get("check_tmp_space", 100)) < 60:
                status.check_tmp_space = "done"
            else:
                status.check_tmp_space = "error"

            if self.socketio_emitter:
                self.socketio_emitter("dry_run", status.__dict__)

        except Exception:
            logger.exception(
                f"An error occurred during dry run for {hostname}"
            )
            status.firewall_rules = "error"
            status.check_ssh_login = "error"
            status.check_dataset_access = "error"
            status.check_tmp_space = "error"

            if self.socketio_emitter:
                self.socketio_emitter("dry_run", status.__dict__)

    def run_dry_run(self, dto: DryRunRequestDTO) -> None:
        """
        Run a dry run on the specified dataset.

        Args:
            dto (DryRunRequestDTO): The request data transfer object
                containing the hostname, username, and dataset name.

        Returns:
            None
        """

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=app_settings.THREAD_WORKS
        ) as executor:
            future = executor.submit(
                asyncio.run,
                self._perform_dry_run_checks(
                    dto.hostname, dto.username, dto.dataset
                ),
            )

            try:
                future.result()
            except Exception:
                logger.exception("Dry run execution failed")

    def _threaded_deploy_task(
        self, lpar_hostname: str, username: str, qualifier: str
    ) -> None:
        """Deploy a task on a remote LPAR.

        Args:
            lpar_hostname (str): The hostname of the LPAR to deploy
                the task on.
            username (str): The username to use for authentication.
            qualifier (str): The qualifier for the task deployment.

        Returns:
            None
        """

        asyncio.run(self._deploy_lpar_loop(lpar_hostname, username, qualifier))

    def schedule_lpar_task(self, dto: ScheduleTaskDTO) -> None:
        """
        Schedules a task to deploy or undeploy a LPAR.

        Parameters:
        - dto (ScheduleTaskDTO): A data transfer object containing
            the necessary information for scheduling the task.

        Returns:
        - None

        Raises:
        - ValueError: If the LPAR ID in the DTO is not found in the repository.
        """

        lpar = self.lpar_repo.get_by_id(self.lpar_repo.model, dto.lpar_id)

        if not lpar:
            logger.error(
                f"LPAR with ID {dto.lpar_id} not found for scheduling."
            )
            return

        self.scheduler_service.schedule_task(
            task_func=self._threaded_deploy_task,
            tag=lpar.lpar,
            schedule_time=dto.schedule_time,
            day_of_week=dto.day_of_week,
            cancel_existing=dto.cancel_jobs,
            lpar_hostname=lpar.hostname,
            username=lpar.username,
            qualifier=lpar.dataset,
        )
        logger.info(
            f"Scheduled task for LPAR {lpar.lpar} at {dto.schedule_time} "
            f"on {dto.day_of_week or 'every_day'}"
        )

    def get_scheduled_tasks(self) -> list[dict[str, Any]]:
        """
        Returns a list of all scheduled tasks.

        Args:
            self (class instance): The class instance on which the method is
                called.

        Returns:
            list[dict[str, Any]]: A list of dictionaries representing each
            scheduled task.
            Each dictionary should contain the following keys and values:
                name (str): The name of the scheduled task.
                schedule (str): The scheduling expression for the task.
                function (str): The name of the function to be executed by
                    the task.
                args (list[Any]): A list of arguments to be passed to
                    the function when it is executed.
                kwargs (dict[str, Any]): A dictionary of keyword arguments
                    to be passed to the function when it is executed.
        """
        return self.scheduler_service.get_all_jobs()

    def clear_scheduled_tasks(self, tag: str | None) -> None:
        """
        Clears all scheduled tasks with the given tag.

        Parameters:
        - tag (str | None): The tag of the scheduled tasks to be cleared.
            If None, all scheduled tasks will be cleared.

        Returns:
        - None
        """

        self.scheduler_service.clear_jobs(tag)
