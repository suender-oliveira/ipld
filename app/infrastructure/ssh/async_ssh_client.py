"""
Provides functions for connecting to an SSH server and running commands.
"""

import os
import re

import asyncssh
import asyncssh.scp

from app.infrastructure.config.settings import app_settings
from app.infrastructure.persistence.repositories import VaultRepository


class AsyncSSHClient:
    """
    Class for connecting to an SSH server and running commands.

    Attributes:
        host (str): The hostname or IP address of the SSH server.
        username (str): The username to authenticate with on
            the SSH server.
        vault_repo (VaultRepository): An instance of the VaultRepository
            class to use for storing and retrieving secrets.
        connection (asyncssh.SSHClientConnection | None): A connected
            SSH client connection.

    Methods:
        _get_private_key_path(self) -> str: Get the private key file for
            a given user.
        connect(self) -> asyncssh.SSHClientConnection: Connect to
            the SSH server and return a connected client.
        close(self) -> None: Close the connection.
        run_command(self, command: str) -> str: Runs a command on
            the SSH connection and returns the output as a string.
        upload_file(self, local_path: str, remote_path: str) -> None: Upload a
            file to a remote server.
        download_file(self, remote_path: str, local_path: str) -> None:
            Download a file from a remote server.
    """

    def __init__(
        self, host: str, username: str, vault_repo: VaultRepository
    ) -> None:
        """
        Initializes a new instance of the SSHClient class.

        Args:
            host (str): The hostname or IP address of the SSH server.
            username (str): The username to authenticate with on
                the SSH server.
            vault_repo (VaultRepository): An instance of the VaultRepository
                class to use for storing and retrieving secrets.

        Returns:
            None
        """

        self.host = host
        self.username = username
        self.connection: asyncssh.SSHClientConnection | None = None
        self.vault_repo = vault_repo

    async def _get_private_key_path(self) -> str:
        """
        Get the private key file for a given user.

        Args:
            self (class instance): The class instance of the method.

        Returns:
            str: The path to the private key file.

        Raises:
            ValueError: If no private key is found for the given user.
            OSError: If an error occurs while creating or writing to
                the private key file.
        """

        keys_from_db = self.vault_repo.read(
            self.vault_repo.model, condition={"username": self.username}
        )

        if not keys_from_db:
            raise_message = f"No private key found for user: {self.username}"
            raise ValueError(raise_message)

        private_key_from_db = re.sub(
            r"\r(?!\$)", "", keys_from_db[0].private_key
        )

        os.makedirs(app_settings.PRIVATE_FILE_PATH, exist_ok=True)

        key_file_path = f"{app_settings.PRIVATE_FILE_PATH}/{self.username}"

        if (
            not os.path.exists(key_file_path)
            or open(key_file_path, encoding="utf-8").read()
            != private_key_from_db
        ):
            try:
                with open(key_file_path, "w", encoding="utf-8") as file:
                    if not private_key_from_db.endswith("\n"):
                        private_key_from_db += "\n"
                    file.write(private_key_from_db)
                os.chmod(key_file_path, 0o600)
            except OSError as error:
                os_error = (
                    "Error creating or writing to the private key file: %s",
                    error,
                )
                raise OSError(os_error) from error
        return key_file_path

    async def connect(self) -> asyncssh.SSHClientConnection:
        """
        Connect to the SSH server and return a connected client.

        Args:
            self (object): The instance of the class that this method
                belongs to.

        Returns:
            asyncssh.SSHClientConnection: A connected SSH client connection.

        Raises:
            Exception: If there is an error connecting to the SSH server.
        """

        if not self.connect:
            key_path = await self._get_private_key_path()
            self._connect = await asyncssh.connect(
                self.host,
                username=self.username,
                client_keys=[key_path],
                known_hosts=None,
            )
        return self._connect

    async def close(self) -> None:
        """
        Close the connection.

        Args:
            self (class instance): The instance of the class.

        Returns:
            None
        """
        if self._connect:
            self._connect.close()

    async def run_command(self, command: str) -> str:
        """
        Runs a command on the SSH connection and returns the output
        as a string.

        Args:
            command (str): The command to run on the SSH connection.

        Returns:
            str: The output of the command as a string.

        Raises:
            Exception: If the command fails or times out.
        """
        connection = await self.connect()

        try:
            result = await connection.run(
                command, check=True, encoding="utf-8"
            )
            return result.stdout.strip()
        finally:
            await self.close()

    async def upload_file(self, local_path: str, remote_path: str) -> None:
        """
        Upload a file to a remote server.

        Args:
            local_path (str): The path of the file on the local machine.
            remote_path (str): The path of the file on the remote server.

        Returns:
            None
        """
        connection = await self.connect()
        try:
            await asyncssh.scp(local_path, (connection, f"{remote_path}"))
        finally:
            await self.close()

    async def download_file(self, remote_path: str, local_path: str) -> None:
        """
        Download a file from a remote server.

        Args:
            remote_path (str): The path of the file on the remote server.
            local_path (str): The path of the file on the local machine.

        Returns:
            None
        """
        connection = await self.connect()
        try:
            await asyncssh.scp((connection, f"{remote_path}"), local_path)
        finally:
            await self.close()
