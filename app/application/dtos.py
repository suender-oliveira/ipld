"""
Defines data transfer objects (DTOs) for application APIs.
"""

from dataclasses import dataclass


@dataclass
class UserCreateDTO:
    """Data Transfer Object for creating a new user."""

    username: str
    password: str
    name: str
    last_name: str


@dataclass
class UserLoginDTO:
    """Data Transfer Object for user login."""

    username: str
    password: str


@dataclass
class LparCreateDTO:
    """Data Transfer Object for creating a new LPAR."""

    lpar: str
    hostname: str
    dataset: str
    username: str  # SSH username for LPAR


@dataclass
class LparUpdateDTO:
    """Data Transfer Object for updating an LPAR."""

    id: int
    lpar: str
    hostname: str
    dataset: str
    username: str
    enabled: int
    schedule: str | None


@dataclass
class VaultEntryCreateDTO:
    """Data Transfer Object for creating a new Vault entry."""

    username: str
    private_key: str
    public_key: str


@dataclass
class TaskRunRequestDTO:
    """Data Transfer Object for requesting LPAR task execution."""

    lpar_ids: list[int]


@dataclass
class DryRunRequestDTO:
    """Data Transfer Object for requesting a dry run."""

    hostname: str
    username: str
    dataset: str


@dataclass
class DryRunStatusDTO:
    """Data Transfer Object for dry run status updates."""

    firewall_rules: str = "wait"
    check_ssh_login: str = "wait"
    check_dataset_access: str = "wait"
    check_tmp_space: str = "wait"


@dataclass
class TaskProgressDTO:
    """Data Transfer Object for task progress updates."""

    result: list[str]  # List of formatted strings like "'hostname': 'status'"
    percent: float
    error: str | None


@dataclass
class ScheduleTaskDTO:
    """Data Transfer Object for scheduling a task."""

    lpar_id: int
    schedule_time: str
    day_of_week: str | None = None
    cancel_jobs: bool | None = False


@dataclass
class ReportFilterDTO:
    """Data Transfer Object for filtering reports."""

    view_type: str  # e.g., "done", "fail", "last_ipl"


@dataclass
class UserApprovalActionDTO:
    """Data Transfer Object for approving/unapproving user access."""

    user_id: int
    action: str  # "unblock" or "block"


@dataclass
class DatabaseImportDTO:
    """Data Transfer Object for importing database content."""

    table_name: str
    data_to_import: str  # JSON string of data
