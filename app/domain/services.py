"""
Provides various utility services for the application.
"""

import hashlib
import hmac
import os
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class IPasswordHasher(ABC):
    """
    An interface for password hashing algorithms.
    """

    @abstractmethod
    def hash_password(self, password: str, salt: bytes | None = None) -> str:
        """
        Hashes a password using the SHA-256 algorithm.

        Args:
            password (str): The password to be hashed.
            salt (bytes | None): An optional salt to be used in the hashing
                process. Defaults to None.

        Returns:
            str: The hashed password as a hexadecimal string.
        """
        pass

    @abstractmethod
    def check_password(
        self, plain_password: str, hashed_password: str
    ) -> bool:
        """
        Check if a given plain password matches a hashed password.

        Args:
            plain_password (str): The plain text password to check.
            hashed_password (str): The hashed password to compare against.

        Returns:
            bool: True if the plain password matches the hashed password,
                False otherwise.
        """
        pass


class PasswordHasher(IPasswordHasher):
    """Hashing passwords using PBKDF2 with a random salt."""

    def __init__(
        self, method: str = "sha256", iterations: int = 100000
    ) -> None:
        """
        Initialize the hash object.

        Args:
            method (str): The hashing algorithm to use. Default is "sha256".
            iterations (int): The number of iterations to perform.
                Default is 100000.

        Returns:
            None
        """
        self.method = method
        self.iterations = iterations

    def hash_password(self, password: str, salt: bytes | None = None) -> str:
        """Hash a password using PBKDF2 with the given parameters.

        Args:
            password (str): The password to be hashed.
            salt (Optional[bytes]): An optional salt value to use for hashing.
                If not provided, a random salt will be generated.

        Returns:
            str: The hexadecimal representation of the hashed password.
        """

        if salt is None:
            salt = os.urandom(16)
        key = hashlib.pbkdf2_hmac(
            self.method, password.encode("utf-8"), salt, self.iterations
        )
        generated_password = salt + key
        return generated_password.hex()

    def check_password(
        self, plain_password: str, hashed_password: str
    ) -> bool:
        """Check if a given password matches a stored hash.

        Args:
            plain_password (str): The plain text password to check.
            hashed_password (str): The hashed password to compare against.

        Returns:
            bool: True if the password matches, False otherwise.

        Raises:
            ValueError: If either the plain or hashed password is empty.
        """

        hashed_password_bytes = bytes.fromhex(hashed_password)
        salt = hashed_password_bytes[:16]
        stored_key = hashed_password_bytes[16:]
        new_key = hashlib.pbkdf2_hmac(
            self.method, plain_password.encode("utf-8"), salt, self.iterations
        )
        return hmac.compare_digest(stored_key, new_key)


class IExternalSSHService(ABC):
    """Interface for SSH services."""

    @abstractmethod
    async def run_command(self, host: str, username: str, command: str) -> str:
        """Run a command on a remote host via SSH.

        Args:
            host (str): The hostname or IP address of the remote host.
            username (str): The username to use for authentication.
            command (str): The command to run on the remote host.

        Returns:
            str: The output of the command as a string.
        """
        pass

    @abstractmethod
    async def upload_file(
        self, host: str, username: str, local_path: str, remote_path: str
    ) -> None:
        """Upload a file to a remote host via SSH.

        Args:
            host (str): The hostname or IP address of the remote host.
            username (str): The username to use for authentication.
            local_path (str): The path to the local file to upload.
            remote_path (str): The destination path on the remote host.
        """
        pass

    @abstractmethod
    async def download_file(
        self, host: str, username: str, remote_path: str, local_path: str
    ) -> None:
        """Download a file from a remote host via SSH.

        Args:
            host (str): The hostname or IP address of the remote host.
            username (str): The username to use for authentication.
            remote_path (str): The source path on the remote host.
            local_path (str): The destination path on the local machine.
        """
        pass


class IDryRunExternalService(ABC):
    """
    An interface for dry-running services.
    """

    @abstractmethod
    async def check_egress_firewall(self, lpar_hostname: str) -> bool:
        """
        Check if egress firewall is enabled on Cirrus for a given LPAR
        hostname.

        Parameters:
        lpar_hostname (str): The hostname of the LPAR to check.

        Returns:
        bool: True if egress firewall is enabled, False otherwise.
        """
        pass

    @abstractmethod
    async def check_ssh_connection(
        self, lpar: str, username: str, syslog_qualifier: str
    ) -> dict[str, Any]:
        """
        Check SSH connection to a Unix Subsystem.

        Parameters:
            lpar (str): The name of the LPAR to check the SSH connection to.
            username (str): The username to use for authentication.
            syslog_qualifier (str): A string to qualify the log message with.

        Returns:
            dict[str, Any]: A dictionary containing the results of
                the SSH connection check.
        """
        pass


class ISchedulerService(ABC):
    """
    An interface for scheduling tasks.
    """

    @abstractmethod
    def schedule_task(
        self,
        task_func: Callable[[], None],
        tag: str,
        schedule_time: str,
        day_of_week: str | None = None,
        cancel_existing: bool = False,
        **kwargs: dict,
    ) -> None:
        """
        Schedules a task to run at a specified time.

        Args:
            task_func (Any): The function to be executed as the task.
            tag (str): A unique identifier for the task.
            schedule_time (str): The time when the task should run, in
                crontab format.
            day_of_week (str | None): Optional. The day of the week when
                the task should run, in lowercase. If not specified, the task
                will run every day.
            cancel_existing (bool): Optional. Whether to cancel any existing
                scheduled tasks with the same tag before scheduling the new
                task. Defaults to False.
            **kwargs (dict): Additional keyword arguments that will be passed
                to the task function when it is executed.

        Returns:
            None
        """
        pass

    @abstractmethod
    def get_all_jobs(self) -> list[dict[str, Any]]:
        """
        Returns a list of all jobs in the system.

        Args:
            self (class instance): The instance of the class calling
                the method.

        Returns:
            list[dict[str, Any]]: A list of dictionaries representing each job.
                Each dictionary should contain the following keys and values:
                    - id (int): The unique identifier for the job.
                    - status (str): The current status of the job, such as
                        "pending", "running", or "completed".
                    - progress (int): The percentage of completion for the job,
                        ranging from 0 to 100.
                    - created_at (datetime): The date and time when the job was
                        created.
                    - started_at (datetime): The date and time when the job
                        began running.
                    - completed_at (datetime): The date and time when the job
                        finished running.
        """
        pass

    @abstractmethod
    def clear_jobs(self, tag: str | None = None) -> None:
        """Clears all scheduled jobs with the given tag.

        Args:
            tag (str | None): The tag of the jobs to be cleared. If None,
                all jobs will be cleared. Defaults to None.

        Returns:
            None
        """
        pass

    @abstractmethod
    def start_scheduler(self) -> None:
        """
        Starts the scheduler.

        Args:
            self (class instance): The instance of the class calling
                the method.

        Returns:
            None
        """
        pass

    @abstractmethod
    def stop_scheduler(self) -> None:
        """
        Stops the scheduler.

        Args:
            self (class instance): The instance of the class calling
                the method.

        Returns:
            None
        """
        pass
