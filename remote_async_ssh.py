"""
A module that defines a RemoteSSHConnection class for establishing and managing a remote 
SSH connection.

The class provides methods for connecting to a remote host, running commands on 
the remote host, uploading and downloading files, and closing the connection.

The class uses the asyncssh library for asynchronous SSH connections, and the 
Database class for retrieving the private key associated with the user 
from a SQLite database.

Usage:
    To use the RemoteSSHConnection class, create an instance of the class with 
    the hostname and username of the remote server, and then call the desired methods 
    on the instance to establish a connection, run commands, and transfer files.
"""

import os
import re
import asyncssh
import asyncssh.scp
# from database import Database
from sqlalchemy_sqlite import CrudDB, Vault

RESULT_PATH = "/zplatipld/database"
ZPLATIPLD_DB = "zplatipld.sqlite3"
ZPLATIPLD_URL_DB = f"sqlite:///{RESULT_PATH}/{ZPLATIPLD_DB}"

class RemoteSSHConnection:
    """A class for establishing and managing a remote SSH connection.

    Args:
        host (str): The hostname or IP address of the remote server.
        username (str): The username used to authenticate with the remote server.

    Attributes:
        host (str): The hostname or IP address of the remote server.
        username (str): The username used to authenticate with the remote server.
        _conn (paramiko.SSHClient): The SSH connection object.

    """

    def __init__(self, host: str, username: str):
        """Initialize the RemoteSSHConnection object.

        Args:
            host (str): The hostname or IP address of the remote server.
            username (str): The username used to authenticate with the remote server.

        """
        self.host = host
        self.username = username
        self._conn = None

    async def check_pkey(self) -> str:
        """Checks if the private key exists locally, and if not, retrieves it
        from the database and saves it to a file.

        Returns:
            str: The path to the private key file.

        Raises:
            OSError: If there is an error creating or writing to the private key file.

        """
        private_file_path = "/zplatipld/secret"
        key_vault_database = CrudDB(ZPLATIPLD_URL_DB)
        keys_from_db = key_vault_database.read(Vault,condition={"username": self.username})
        print(keys_from_db[0])
        private_key_from_db = re.sub(r"\r(?!\$)", "", keys_from_db[0].private_key)

        if not os.path.exists(private_file_path):
            os.makedirs(private_file_path)

        key_file_path = f"{private_file_path}/{self.username}"

        if not os.path.exists(key_file_path):
            try:
                with open(key_file_path, "w", encoding="utf-8") as file:
                    if not private_key_from_db.endswith("\n"):
                        private_key_from_db += "\n"
                    file.write(private_key_from_db)
                os.chmod(key_file_path, 0o600)
            except OSError as error:
                raise OSError(
                    f"Error creating or writing to the private key file: {error}"
                ) from error
        return key_file_path

    async def connect(self) -> asyncssh.SSHClientConnection:
        """Establishes a SSH connection to the remote host using 
        the private key associated with the user.

        If the private key is not available locally, this method retrieves it 
        from the database and saves it to a file.

        Returns:
            asyncssh.SSHClientConnection: A SSH client connection object.

        Raises:
            asyncssh.Error: If there is an error establishing the SSH connection.

        """
        key_path = await self.check_pkey()
        self._conn = await asyncssh.connect(
            self.host, username=self.username, client_keys=[key_path], known_hosts=None
        )
        return self._conn

    async def close(self):
        """Closes the SSH connection to the remote host, if it is currently open.

        This method calls the close() method of the underlying SSH client connection object, 
        if it exists. Once the connection is closed, the reference to the connection object 
        is set to None.

        """
        if self._conn:
            self._conn.close()
            self._conn = None

    async def run_command(self, command: str) -> str:
        """Runs the specified command on the remote host and returns its output as a string.

        This method establishes an SSH connection to the remote host, runs the specified 
        command using the connection object, retrieves the output of the command, closes 
        the connection, and returns the output as a string. If there is an error
        running the command or establishing the SSH connection, an exception is raised.

        Args:
            command (str): The command to run on the remote host.

        Returns:
            str: The output of the command as a string.

        Raises:
            asyncssh.Error: If there is an error establishing the SSH connection or 
            running the command.

        """
        conn = await self.connect()
        result = await conn.run(command)
        output = result.stdout.strip()
        await self.close()
        return output

    async def upload_file(self, local_path: str, remote_path: str) -> None:
        """Uploads a file from the local machine to the remote host.

        This method establishes an SSH connection to the remote host, uses 
        the connection object to upload a file from the local machine to 
        the remote host using the asyncssh.scp() method, and closes 
        the connection. If there is an error uploading the file or establishing
        the SSH connection, an exception is raised.

        Args:
            local_path (str): The path to the local file to upload.
            remote_path (str): The path on the remote host where the file should be uploaded.

        Raises:
            asyncssh.Error: If there is an error establishing the SSH connection or 
            uploading the file.

        """
        conn = await self.connect()
        await asyncssh.scp(local_path, (conn, f"{remote_path}"))
        await self.close()

    async def download_file(self, remote_path: str, local_path: str) -> None:
        """Downloads a file from the remote host to the local machine.

        This method establishes an SSH connection to the remote host, uses the connection object
        to download a file from the remote host to the local machine using the asyncssh.scp() 
        method, and closes the connection. If there is an error downloading the file or 
        establishing the SSH connection, an exception is raised.

        Args:
            remote_path (str): The path on the remote host to the file to download.
            local_path (str): The path on the local machine where the file should be saved.

        Raises:
            asyncssh.Error: If there is an error establishing the SSH connection or 
            downloading the file.

        """
        conn = await self.connect()
        await asyncssh.scp((conn, f"{remote_path}"), local_path)
        await self.close()
