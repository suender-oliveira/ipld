import logging
import os
from collections.abc import Callable

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
)
from flask_login import LoginManager, login_required
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect

# Presentation Layer Imports (Blueprints)
from app.api.auth import create_auth_blueprint
from app.api.lpar_management import create_lpar_blueprint
from app.api.report_viewer import create_report_blueprint
from app.api.task_management import create_task_blueprint

# Application Layer Imports
from app.application.services.auth_service import AuthService
from app.application.services.lpar_service import LparService
from app.application.services.report_service import ReportService
from app.application.services.task_service import TaskService
from app.application.use_cases.deploy_lpar_task import DeployLparTaskUseCase
from app.application.use_cases.dry_run_check import DryRunCheckUseCase
from app.application.use_cases.schedule_lpar_task import (
    ScheduleLparTaskUseCase,
)

# Domain Layer Imports (Concrete Implementations of Interfaces)
from app.domain.services import (
    IDryRunExternalService,
    IExternalSSHService,
    PasswordHasher,
)

# Configuration
from app.infrastructure.config.settings import app_settings
from app.infrastructure.external_apis.cirrus_client import CirrusClient
from app.infrastructure.ingest.ipl_data_ingest import IPLDataIngestor

# Infrastructure Layer Imports (Concrete Implementations)
from app.infrastructure.persistence.repositories import (
    LparRepository,
    ResultsDoneRepository,
    ResultsFailRepository,
    ResultsLastIplRepository,
    SQLAlchemyRepository,
    UserRepository,
    VaultRepository,
)
from app.infrastructure.scheduler.task_scheduler import AppScheduler
from app.infrastructure.ssh.async_ssh_client import AsyncSSHClient

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# --- Flask App Initialization ---
app = Flask(__name__)
app.config["SECRET_KEY"] = app_settings.SECRET_KEY
app.config["ENVIRONMENT"] = app_settings.ENVIRONMENT
app.template_folder = os.path.join(os.path.dirname(__file__), "../templates")
socketio = SocketIO(app)
csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.login_view = "auth_bp.login"
login_manager.init_app(app)

# --- Dependency Injection Setup ---
# Infrastructure Layer Instances
db_repository = SQLAlchemyRepository(app_settings.ZPLATIPLD_URL_DB)
lpar_repo = LparRepository(app_settings.ZPLATIPLD_URL_DB)
user_repo = UserRepository(app_settings.ZPLATIPLD_URL_DB)
vault_repo = VaultRepository(app_settings.ZPLATIPLD_URL_DB)
results_done_repo = ResultsDoneRepository(app_settings.ZPLATIPLD_URL_DB)
results_fail_repo = ResultsFailRepository(app_settings.ZPLATIPLD_URL_DB)
results_last_ipl_repo = ResultsLastIplRepository(app_settings.ZPLATIPLD_URL_DB)
cirrus_client = CirrusClient()
app_scheduler = AppScheduler()
ipl_data_ingestor = IPLDataIngestor(app_settings.ZPLATIPLD_URL_DB)


# Domain Layer Service Implementations (proxies to Infrastructure)
class SSHServiceAdapter(IExternalSSHService):
    """Adapter class for SSH external service."""

    def __init__(
        self, async_ssh_client_factory: Callable[[str, str], AsyncSSHClient]
    ) -> None:
        self._async_ssh_client_factory = async_ssh_client_factory

    async def run_command(self, host: str, username: str, command: str) -> str:
        client = self._async_ssh_client_factory(host, username)
        return await client.run_command(command)

    async def upload_file(
        self, host: str, username: str, local_path: str, remote_path: str
    ) -> None:
        client = self._async_ssh_client_factory(host, username)
        await client.upload_file(local_path, remote_path)

    async def download_file(
        self, host: str, username: str, remote_path: str, local_path: str
    ) -> None:
        client = self._async_ssh_client_factory(host, username)
        await client.download_file(remote_path, local_path)


# Factory for AsyncSSHClient to inject vault_repo
def async_ssh_client_factory(host: str, username: str) -> AsyncSSHClient:
    return AsyncSSHClient(host=host, username=username, vault_repo=vault_repo)


ssh_service = SSHServiceAdapter(async_ssh_client_factory)


class DryRunExternalServiceAdapter(IDryRunExternalService):
    """Adapter class for dry run external service."""

    def __init__(
        self,
        cirrus_client_instance: CirrusClient,
        ssh_service_instance: IExternalSSHService,
    ) -> None:
        self._cirrus_client = cirrus_client_instance
        self._ssh_service = ssh_service_instance

    async def check_egress_firewall(self, lpar_hostname: str) -> bool:
        return self._cirrus_client.check_egress_firewall(lpar_hostname)

    async def check_ssh_connection(
        self, lpar: str, username: str, syslog_qualifier: str
    ) -> dict:
        remote_ssh_checks = {}
        try:
            check_ssh_login = await self._ssh_service.run_command(
                lpar, username, "cd $HOME; pwd 2>&1"
            )
            remote_ssh_checks["check_ssh_login"] = check_ssh_login.split("/")[
                -1
            ]
            check_dataset_access = await self._ssh_service.run_command(
                lpar,
                username,
                (
                    (
                        (
                            f'check=$(tsocmd "listcat level({syslog_qualifier})"'
                            "command= | grep NONVSAM"
                            ' | egrep "LOG|BLDR01" | tail -2 |'
                            " head -1 |" + ' cut -d" " -f3)'
                        )
                        + " && "
                    )
                    + "head -1000 \"//'$check'\" | wc -l 2>&1"
                ),
            )
            remote_ssh_checks["check_dataset_access"] = check_dataset_access
            check_tmp_space = await self._ssh_service.run_command(
                lpar, username, "df -kP /tmp | tail -1 | awk '{print $5}'"
            )
            remote_ssh_checks["check_tmp_space"] = check_tmp_space.replace(
                "%", ""
            )

        except Exception as error:
            logger.exception("Error during SSH connection checks for dry run")
            remote_ssh_checks["check_ssh_login"] = str(error)

        return remote_ssh_checks


dry_run_external_service = DryRunExternalServiceAdapter(
    cirrus_client, ssh_service
)
password_hasher = PasswordHasher()

# Application Layer Service Instances
auth_service = AuthService(
    user_repo=user_repo, password_hasher=password_hasher
)
lpar_service = LparService(lpar_repo=lpar_repo)
task_service = TaskService(
    lpar_repo=lpar_repo,
    ssh_service=ssh_service,
    dryrun_ssh_service=dry_run_external_service,
    scheduler_service=app_scheduler,
    cirrus_client=cirrus_client,
)
report_service = ReportService(
    results_done_repo=results_done_repo,
    results_fail_repo=results_fail_repo,
    results_last_ipl_repo=results_last_ipl_repo,
    ipl_data_ingestor=ipl_data_ingestor,
)

# Application Layer Use Cases
deploy_lpar_task_use_case = DeployLparTaskUseCase(task_service=task_service)
dry_run_check_use_case = DryRunCheckUseCase(task_service=task_service)
schedule_lpar_task_use_case = ScheduleLparTaskUseCase(
    task_service=task_service
)

# --- Register Blueprints ---
# Pass socketio.emit directly to blueprints that need it for real-time updates
app.register_blueprint(
    create_auth_blueprint(auth_service, login_manager.user_loader)
)
app.register_blueprint(
    create_lpar_blueprint(lpar_service, dry_run_check_use_case, socketio.emit)
)
app.register_blueprint(
    create_task_blueprint(
        task_service,
        deploy_lpar_task_use_case,
        schedule_lpar_task_use_case,
        socketio.emit,
    )
)
app.register_blueprint(create_report_blueprint(report_service))


# --- General Routes (if any left after refactoring, often for home/health) ---
@app.route("/health/ping", methods=["GET"])
def health_check() -> tuple[Response, int]:
    """Simple health check endpoint."""
    return jsonify({"status": "available"}), 200


@app.route("/back", methods=["GET"])
def back() -> Response:
    """Redirects to the previous page."""
    return redirect(request.referrer)


@app.route("/", methods=["GET"])
@login_required
def index() -> str:
    """Home page route, requires login."""
    return render_template("index.html")


# --- Application Context Processor ---
@app.context_processor
def inject_app() -> dict[str, Flask]:
    """Injects the Flask app object into Jinja2 templates."""
    return {"app": app}


# --- Main Application Run ---
if __name__ == "__main__":
    logger.info("Initializing database...")
    db_repository.init_database()
    logger.info("Starting scheduler thread...")
    app_scheduler.start()
    logger.info("Starting Flask application with SocketIO...")
    socketio.run(
        app,
        allow_unsafe_werkzeug=True,  # Development only
        host="0.0.0.0",
        port=8000,
        debug=True,
    )
