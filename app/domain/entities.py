"""
Defines data entities used throughout the application.
"""

from dataclasses import dataclass


@dataclass
class User:
    """
    Represents a user in the system.
    """

    id: int | None
    username: str
    password: str | None = None
    name: str | None = None
    last_name: str | None = None
    approved: int = 0


@dataclass
class Lpar:
    """
    Represents an LPAR (Logical Parition) on z/OS
    """

    id: int | None
    lpar: str
    hostname: str
    dataset: str
    username: str
    enable: int = 0
    schedule: str | None = None


@dataclass
class VaultEntry:
    """
    Represents an SSH key entry in the vault.
    """

    id: int | None
    username: str
    private_key: str
    public_key: str


@dataclass
class IPLResultDone:
    """
    Represents a successful IPL analysis result.
    """

    id: int | None
    sysname: str
    ipl_date: str
    log_dataset: str
    shutdown_begin: str
    shutdown_end: str
    ipl_begin: str
    ipl_end: str
    pre_ipl: str
    pos_ipl: str
    shutdown_duration: str
    poweroff_duration: str
    load_ipl: str
    total_duration: str


@dataclass
class IPLResultFail:
    """
    Represents the failed IPL analysis result.
    """

    id: int | None
    sysname: str
    log_dataset: str
    shutdown_begin: str
    shutdown_end: str
    ipl_begin: str
    ipl_end: str
    pre_ipl: str
    pos_ipl: str


@dataclass
class IPLResultLast:
    """
    Represents the last IPL analysis result for a system.
    """

    id: int | None
    sysname: str
    ipl_date: str
    log_dataset: str
