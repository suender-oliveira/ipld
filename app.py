import asyncio
import hashlib
import hmac
import time
import os
import concurrent.futures
import shutil
import threading
from threading import Thread
import logging
from flask import (
    Flask,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    session,
    jsonify,
    send_from_directory,
    abort,
    current_app,
)
from flask_socketio import SocketIO
from flask_login import (
    LoginManager,
    UserMixin,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import schedule

from sqlalchemy_sqlite import (
    CrudDB,
    ResultsDoneTable,
    ResultsFailTable,
    ResultsLastIplTable,
    Users,
    Lpar,
    Vault,
)
from dry_run import DryRun
from remote_async_ssh import RemoteSSHConnection
from zplatipld_ingest import duration_ingest, zplatipld_ingest

# Loading dotenv
load_dotenv()

logging.basicConfig(level=logging.DEBUG)

THREAD_WORKERS = 60
global TASK_STOP_RUNNING
RESULT_PATH = "/zplatipld/database"
ZPLATIPLD_DB = "zplatipld.sqlite3"
ZPLATIPLD_URL_DB = f"sqlite:///{RESULT_PATH}/{ZPLATIPLD_DB}"
ZPLATIPLD_RESULTS_LAST_IPL_TABLE = "results_last_ipl"
ZPLATIPLD_RESULTS_DONE_TABLE = "results_done"
ZPLATIPLD_RESULTS_FAIL_TABLE = "results_fail"
ZPLATIPLD_RESULTS_GARB_TABLE = "results_garb"
PRIVATE_FILE_PATH = "/zplatipld/secret"
ROOT_RESULTS = "/zplatipld/results"
ROOT_TMP_ANALYSIS = "/tmp/ipl_analysis/"
IPL_DB_LPAR = "ipld_db_lpar.db"
IPL_DB_USER = "ipld_db_user.db"

# HTML Constants
LOGIN_HTML = "login.html"
VAULT_SSH_HTML = "vault_ssh.html"
LPAR_SETTINGS_HTML = "lpar_settings.html"
LPAR_SETTINGS_DET_HTML = "lpar_settings_detail.html"


def generate_password_hash(
    password,
    method,
    salt=None,
):
    """
    This method is used to generate a password hash
    Parameters:
    - password (str): Plaintext password to hash
    - method (str): Algorithm that will use for build the hash

    Returns (str): hexadecimal hash of password

    """
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac(method, password.encode("utf-8"), salt, 100000)
    generated_password = salt + key
    return generated_password.hex()


def check_password_hash(plain_password, hashed_password, method):
    """
    This method is used to generate a password hash
    Parameters:
    - plain_password (str): Plaintext password to hash
    - hashed_password (str): Hexadecimal hash of password
    - method (str): Algorithm that will use for decode the hash

    Returns (bool): True or False

    """
    hashed_password_hex = bytes.fromhex(hashed_password)
    salt = hashed_password_hex[:16]
    stored_key = hashed_password_hex[16:]
    new_key = hashlib.pbkdf2_hmac(
        method, plain_password.encode("utf-8"), salt, 100000
    )
    return hmac.compare_digest(stored_key, new_key)


async def run_ssh_command(host, username, command):
    """This is an asynchronous Python function that establishes an SSH connection to a remote host
    and runs a command on it.

    Parameters
    ----------
    host
    The host parameter is the IP address or hostname of the remote server that the SSH connection
    will be established with.

    username
    The username parameter is a string that represents the username used to authenticate the SSH
    connection to the host.

    command
    The command parameter is a string that represents the command to be executed on the remote
    host via SSH. For example, it could be "ls -l" to list the files in the current directory.

    Returns
    -------
    The function `run_ssh_command` is returning the result of running the command on the remote SSH
    connection. The specific data type of the return value depends on the implementation of the
    `run_command` method in the `RemoteSSHConnection` class. It could be a string, a list of
    strings, or some other data type depending on the output of the command.

    """
    ssh_client = RemoteSSHConnection(host, username)
    return await ssh_client.run_command(command)


async def run_scp_send(host, username, local_path, remote_path):
    """This is an asynchronous Python function that uploads a local file to a remote server
    using SCP protocol.

    Parameters
    ----------
    host
    The hostname or IP address of the remote server where the file will be uploaded.

    username
    The username parameter is a string that represents the username used to authenticate the SSH
    connection to the remote host.

    local_path
    The local path is the path to the file or directory on the local machine that you want to upload
    to the remote server. For example, if you want to upload a file called "example.txt" located in
    the "Documents" folder on your local machine, the local path would be "/Users/

    remote_path
    The `remote_path` parameter is a string representing the path to the destination file or
    directory on the remote server where the `local_path` file will be uploaded to.

    Returns
    -------
    The `run_scp_send` function is returning the result of the `upload_file` method of the
    `RemoteSSHConnection` class, which is an awaitable object that represents the completion
    of the file upload operation. The return value could be a success/failure status or any
    other relevant information about the upload process.

    """
    ssh_client = RemoteSSHConnection(host, username)
    return await ssh_client.upload_file(local_path, remote_path)


async def run_scp_receive(host, username, local_path, remote_path):
    """This is an asynchronous Python function that downloads a file from a remote server
    using SCP protocol.

    Parameters
    ----------
    host
    The hostname or IP address of the remote server that you want to connect to via SSH.

    username
    The username parameter is a string that represents the username used to authenticate the SSH
    connection to the remote host.

    local_path
    The local path is the path on the local machine where the downloaded file will be saved.

    remote_path
    The path of the file on the remote server that you want to download.

    Returns
    -------
    The function `run_scp_receive` is returning the result of calling the `download_file`
    method of the `ssh_client` object, which is the result of downloading a file from
    the remote server at `remote_path` and saving it to the local file path `local_path`.
    The return value of the `download_file`. The return value could be a success/failure
    status or any other relevant information about the upload process.
    """
    ssh_client = RemoteSSHConnection(host, username)
    return await ssh_client.download_file(remote_path, local_path)


async def deploy_loop(lpar_hostname, username, qualifier):
    """This is an async function that deploys files to a remote server, runs a script, and
    receives CSV files as output.

    Parameters
    ----------
    lpar_hostname
    The hostname of the LPAR (Logical PARtition) to deploy to.

    username
    The username used to connect to the LPAR via SSH.

    qualifier
    The qualifier parameter is a string that is used as an argument for the main.sh script in
    the SSH command. It is passed to the script to specify additional options or configurations
    for the IPL analysis.

    Returns
    -------
    the string value of the `lpar_hostname` variable.

    """

    # Getting local dir
    local_dir = os.path.dirname(os.path.abspath(__file__))

    lpar_name = lpar_hostname.split(".")
    checking_ipl_space = await run_ssh_command(
        lpar_hostname,
        username,
        f"if [[ -d {ROOT_TMP_ANALYSIS}{lpar_name[0]} ]]; then "
        f"rm -rf {ROOT_TMP_ANALYSIS}{lpar_name[0]} && "
        f"mkdir -p {ROOT_TMP_ANALYSIS}{lpar_name[0]}; "
        f"else; mkdir -p {ROOT_TMP_ANALYSIS}{lpar_name[0]}; fi; "
        f"ls -la {ROOT_TMP_ANALYSIS}{lpar_name[0]}",
    )

    if checking_ipl_space:
        files_to_load = [
            "ipld_calc.awk",
            "ipld_parsing.awk",
            "patterns",
            "main.sh",
            "methods.sh",
        ]
        for file_to_load in files_to_load:
            await run_scp_send(
                lpar_hostname,
                username,
                os.path.join(local_dir, file_to_load),
                f"{ROOT_TMP_ANALYSIS}{lpar_name[0]}",
            )

        await run_ssh_command(
            lpar_hostname,
            username,
            f"{ROOT_TMP_ANALYSIS}{lpar_name[0]}/main.sh -r cli -a {lpar_hostname} -q {qualifier}",
        )

        if not os.path.isdir(
            os.path.join(local_dir, f"{ROOT_RESULTS}/{lpar_name[0]}")
        ):
            os.makedirs(
                os.path.join(local_dir, f"{ROOT_RESULTS}/{lpar_name[0]}")
            )
            await run_scp_receive(
                lpar_hostname,
                username,
                os.path.join(local_dir, f"{ROOT_RESULTS}/{lpar_name[0]}"),
                f"{ROOT_TMP_ANALYSIS}{lpar_name[0]}/*.CSV",
            )

        else:
            shutil.rmtree(f"{ROOT_RESULTS}/{lpar_name[0]}")
            os.makedirs(
                os.path.join(local_dir, f"{ROOT_RESULTS}/{lpar_name[0]}")
            )
            await run_scp_receive(
                lpar_hostname,
                username,
                os.path.join(local_dir, f"{ROOT_RESULTS}/{lpar_name[0]}"),
                f"{ROOT_TMP_ANALYSIS}{lpar_name[0]}/*.CSV",
            )
        await run_ssh_command(
            lpar_hostname,
            username,
            f"if [[ -d {ROOT_TMP_ANALYSIS}{lpar_name[0]} ]]; then "
            f"rm -rf {ROOT_TMP_ANALYSIS}{lpar_name[0]} && "
            f"mkdir -p {ROOT_TMP_ANALYSIS}{lpar_name[0]}; "
            f"else; mkdir -p {ROOT_TMP_ANALYSIS}{lpar_name[0]}; fi; "
            f"ls -la {ROOT_TMP_ANALYSIS}{lpar_name[0]}",
        )

    else:
        return "ERROR"

    await run_ssh_command(
        lpar_hostname,
        username,
        "if [[ -d /tmp/ipl_analysis ]]; then rm -rf /tmp/ipl_analysis; fi",
    )

    return f"{lpar_hostname}"


def deploy_execution(*identifiers):
    """This function deploys code execution on multiple LPARs concurrently using
    a ThreadPoolExecutor and updates the progress and results to the client using SocketIO.

    Returns
    -------
    a list of results from the completed tasks.

    """

    identifiers_list = tuple(identifiers)
    lpares_dic = []
    lpar_database = CrudDB(ZPLATIPLD_URL_DB)
    lpars_from_db = lpar_database.read(Lpar, in_values={"id": identifiers_list})

    for lpar_row_db in lpars_from_db:
        lpares_dic.append(f"'{lpar_row_db.hostname}': 'wait'")

    socketio.emit(
        "task_progress",
        {
            "result": lpares_dic,
            "percent": 10,
            "error": None,
        },
    )

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=THREAD_WORKERS
    ) as executor:
        futures = []
        results = []
        check_lpars = []
        send_error = []

        for lpar_lines in lpars_from_db:
            check_lpars.append(lpar_lines.lpar)
            future_executor = executor.submit(
                asyncio.run,
                deploy_loop(
                    lpar_lines.hostname, lpar_lines.username, lpar_lines.dataset
                ),
            )
            futures.append(future_executor)

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                socketio.emit("task_completed", results)
            except Exception as error:
                send_error = str(error)

            for i in results:
                for i_dict, lpares_val in enumerate(lpares_dic):
                    if i in lpares_val:
                        lpares_dic[i_dict] = lpares_val.replace(
                            "'wait'", "'done'"
                        )

                    if check_lpars:
                        for check_lpar in check_lpars:
                            if (
                                check_lpar in lpares_val
                                and "done" in lpares_val
                            ):
                                check_lpars.remove(check_lpar)

            percent_of_progress = (len(results) / len(futures)) * 100
            socketio.emit(
                "task_progress",
                {
                    "result": lpares_dic,
                    "percent": percent_of_progress,
                    "error": send_error,
                },
            )

        if check_lpars:
            for check_lpar in check_lpars:
                for i, lpares in enumerate(lpares_dic):
                    if check_lpar in lpares:
                        lpares_dic[i] = lpares.replace("'wait'", "'error'")

        percent_of_progress = (len(results) / len(futures)) * 100
        socketio.emit(
            "task_progress",
            {
                "result": lpares_dic,
                "percent": percent_of_progress,
                "error": send_error,
            },
        )

        # Waiting all tasks to be concluded
        done, _ = concurrent.futures.wait(futures)

        # Getting the concluded tasks results
        results = [f.result() for f in done]

        # Printing tasks that are still in progress
        print([f for f in futures if not f.done()])

        # Las update to the client
        socketio.emit(
            "task_progress",
            {
                "result": lpares_dic,
                "percent": percent_of_progress,
                "error": send_error,
            },
        )

        return results


async def dry_run(lpar, username, syslog_qualifier):
    results_websocket = {
        "firewall_rules": "wait",
        "check_ssh_login": "wait",
        "check_dataset_access": "wait",
        "check_tmp_space": "wait",
    }

    socketio.emit("dry_run", results_websocket)

    dry_run_object = DryRun(lpar, username, syslog_qualifier)

    check_firewall_rules = await dry_run_object.check_egress_firewall()

    results = {}
    if check_firewall_rules == 1:
        results_websocket["firewall_rules"] = "done"
        results["firewall_rules"] = "done"
        socketio.emit("dry_run", results_websocket)

        check_remotes = await dry_run_object.check_ssh_connection()

        print(check_remotes[0])

        if check_remotes[0]["check_ssh_login"] == username:
            results_websocket["check_ssh_login"] = "done"
            results["check_ssh_login"] = "done"
            socketio.emit("dry_run", results_websocket)
        else:
            results_websocket["check_ssh_login"] = "error"
            results["check_ssh_login"] = "error"
            socketio.emit("dry_run", results_websocket)

        if int(check_remotes[1]["check_dataset_access"]) > 1:
            results_websocket["check_dataset_access"] = "done"
            results["check_dataset_access"] = "done"
            socketio.emit("dry_run", results_websocket)
        else:
            results_websocket["check_dataset_access"] = "error"
            results["check_dataset_access"] = "error"
            socketio.emit("dry_run", results_websocket)

        if int(check_remotes[2]["check_tmp_space"]) < 60:
            results_websocket["check_tmp_space"] = "done"
            results["check_tmp_space"] = "done"
            socketio.emit("dry_run", results_websocket)
        else:
            results_websocket["check_tmp_space"] = "error"
            results["check_tmp_space"] = "error"
            socketio.emit("dry_run", results_websocket)

    elif check_firewall_rules == 0:
        results["firewall_rules"] = "error"
    else:
        results["firewall_rules"] = "error"
    socketio.emit("dry_run", results)


def dry_run_execution(lpar, username, syslog_qualifier):
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        results = []

        future_executor = executor.submit(
            asyncio.run, dry_run(lpar, username, syslog_qualifier)
        )
        futures.append(future_executor)

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                # socketio.emit("dry_run", results)
            except Exception as error:
                socketio.emit("dry_run", {future.result(): "fail"})
                return str(error)

        # Waiting all tasks to be concluded
        done, _ = concurrent.futures.wait(futures)

        # Getting the concluded tasks results
        results = [f.result() for f in done]

        # Printing tasks that are still in progress
        print([f for f in futures if not f.done()])


def run_task_scheduler_threads(lpar_hostname, username, qualifier):
    asyncio_coroutine_run = lambda: asyncio.run(
        deploy_loop(lpar_hostname, username, qualifier)
    )
    job_thread = threading.Thread(target=asyncio_coroutine_run)
    job_thread.start()


def task_scheduler_set(
    lpar_hostname,
    username,
    dataset,
    received_tag,
    schedule_time,
    day_of_week=None,
    cancel_jobs=None,
):
    if cancel_jobs:
        schedule.clear()
    elif day_of_week == "sunday":
        job = (
            schedule.every()
            .sunday.at(schedule_time)
            .do(
                run_task_scheduler_threads,
                lpar_hostname=lpar_hostname,
                username=username,
                qualifier=dataset,
            )
            .tag(received_tag)
        )
    elif day_of_week == "monday":
        job = (
            schedule.every()
            .monday.at(schedule_time)
            .do(
                run_task_scheduler_threads,
                lpar_hostname=lpar_hostname,
                username=username,
                qualifier=dataset,
            )
            .tag(received_tag)
        )
    elif day_of_week == "tuesday":
        job = (
            schedule.every()
            .tuesday.at(schedule_time)
            .do(
                run_task_scheduler_threads,
                lpar_hostname=lpar_hostname,
                username=username,
                qualifier=dataset,
            )
            .tag(received_tag)
        )
    elif day_of_week == "wednesday":
        job = (
            schedule.every()
            .wednesday.at(schedule_time)
            .do(
                run_task_scheduler_threads,
                lpar_hostname=lpar_hostname,
                username=username,
                qualifier=dataset,
            )
            .tag(received_tag)
        )
    elif day_of_week == "thursday":
        job = (
            schedule.every()
            .thursday.at(schedule_time)
            .do(
                run_task_scheduler_threads,
                lpar_hostname=lpar_hostname,
                username=username,
                qualifier=dataset,
            )
            .tag(received_tag)
        )
    elif day_of_week == "friday":
        job = (
            schedule.every()
            .friday.at(schedule_time)
            .do(
                run_task_scheduler_threads,
                lpar_hostname=lpar_hostname,
                username=username,
                qualifier=dataset,
            )
            .tag(received_tag)
        )
    elif day_of_week == "saturday":
        job = (
            schedule.every()
            .saturday.at(schedule_time)
            .do(
                run_task_scheduler_threads,
                lpar_hostname=lpar_hostname,
                username=username,
                qualifier=dataset,
            )
            .tag(received_tag)
        )
    elif day_of_week is None:
        job = {
            schedule.every()
            .day.at(schedule_time)
            .do(
                run_task_scheduler_threads,
                lpar_hostname=lpar_hostname,
                username=username,
                qualifier=dataset,
            )
            .tag(received_tag)
        }


def task_scheduler_manager():
    lpar_database = CrudDB(ZPLATIPLD_URL_DB)
    lpar_list_db = lpar_database.read(Lpar)
    try:
        for lpar in lpar_list_db:
            if len(lpar.schedule) > 8:
                lpar_schedule = lpar.schedule.split()
                task_scheduler_set(
                    lpar.hostname,
                    lpar.username,
                    lpar.dataset,
                    lpar.lpar,
                    lpar_schedule[1],
                    day_of_week=lpar_schedule[0],
                    cancel_jobs=None,
                )
            else:
                task_scheduler_set(
                    lpar.hostname,
                    lpar.username,
                    lpar.dataset,
                    lpar.lpar,
                    lpar.schedule,
                    day_of_week=None,
                    cancel_jobs=None,
                )
        while True:
            schedule.run_pending()
            time.sleep(1)
    except Exception as error:
        print(str(error))


# Running Web Server with Flasks
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["ENVIRONMENT"] = os.getenv("ENVIRONMENT")
app.template_folder = os.path.join(os.path.dirname(__file__), "templates")
socketio = SocketIO(app)
csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.login_view = "login_form"
login_manager.init_app(app)


@app.context_processor
def inject_app():
    """The function returns a dictionary with a key "app" and its value being the variable "app".

    Returns
    -------
    A dictionary containing a key-value pair where the key is "app" and the value is the variable
    "app".

    """
    return {"app": app}


class User(UserMixin):
    """
    The above class is a user class that inherits from the UserMixin class.
    """

    def __init__(self, id_, username, password, approved):
        """This is a constructor function that initializes the attributes of a user object with an
        ID, username, password, and approval status.

        Parameters
        ----------
        id_
        The id_ parameter is a unique identifier for the user. It could be an integer or a string
        that uniquely identifies the user in the system.

        username
        The username parameter is a string that represents the username of a user. It is used to
        identify the user and is typically unique for each user.

        password
        The `password` parameter is a string that represents the user's password. It is one of the
        attributes of the class that is being initialized in the `__init__` method.

        approved
        The "approved" parameter is a boolean value that indicates whether the user account has
        been approved or not. If the value is True, it means the account has been approved, and if
        it's False, it means the account is still pending approval.

        """
        self.id = id_
        self.username = username
        self.password = password
        self.approved = approved


@login_manager.user_loader
def load_user(user_id):
    """The function loads a user from a database based on their user ID.

    Parameters
    ----------
    user_id
    The user ID is a unique identifier for a specific user in the database. It is used as
    a parameter to retrieve information about that user from the database.

    Returns
    -------
    The function `load_user` returns a `User` object if a user with the given `user_id` exists in
    the database, otherwise it returns `None`.

    """
    try:
        user_db = CrudDB(ZPLATIPLD_URL_DB)
        user = user_db.read(Users, condition={"id": user_id})
        return (
            User(
                user[0].id, user[0].username, user[0].password, user[0].approved
            )
            if user[0].username
            else None
        )
    except Exception as error:
        print(f"An error occurred: {error}")
        logout


@app.route("/health/ping", methods=["GET"])
def health_check():
    return jsonify({"status": "available"}), 200


@app.route("/back", methods=["GET"])
def back():
    return redirect(request.referrer)


@app.route("/login", methods=["POST"])
def do_login():
    """This function logs in a user by checking their username and password against a database and
    returns a rendered template based on the success or failure of the login attempt.

    Returns
    -------
    If the username and password are correct, the function returns the rendered "index.html"
    template with the IP address passed as a parameter. If the username or password is incorrect,
    the function returns the rendered "login.html" template with a notification message indicating
    that the username or password is incorrect.

    """
    username = request.form["username"]
    password = request.form["password"]

    user_db = CrudDB(ZPLATIPLD_URL_DB)
    user = user_db.read(Users, condition={"username": username})

    try:
        if username == user[0].username:
            if check_password_hash(password, user[0].password, "sha256"):
                session["approved"] = user[0].approved
                userl = User(
                    user[0].id,
                    user[0].username,
                    user[0].password,
                    user[0].approved,
                )
                login_user(userl)
                return render_template("index.html")
    except Exception as error:
        print(str(error))
        logout()

    return render_template(
        LOGIN_HTML,
        notification=("danger", "Username or password is incorrect."),
    )


@app.route("/logout", methods=["GET"])
@login_required
def logout():
    """This function logs out the user and returns a rendered login template with a success
    notification.

    Returns
    -------
    The function `logout()` is returning a rendered template of the login page with a notification
    message indicating that the user has been successfully logged out.

    """
    logout_user()
    return render_template(LOGIN_HTML, notification=("success", "Logged out."))


@app.route("/", methods=["GET"])
@login_required
def index():
    """This function returns the rendered template "index.html"

    Returns
    -------
    The function `index()` is returning the rendered template "index.html"

    """
    return render_template("index.html")


@app.route("/login/render")
def login_form():
    """This function returns the login form HTML template.

    Returns
    -------
    The function `login_form()` is returning the rendered template "login.html".

    """
    return render_template(LOGIN_HTML)


@app.route("/signup", methods=["GET"])
def signup():
    """This function renders a signup.html template and passes an ip_address variable to it.

    Returns
    -------
    The function `signup()` is returning the rendered HTML template "signup.html".

    """
    return render_template("signup.html")


@app.route("/signup/save", methods=["POST"])
def signup_save():
    """This function saves user information to a database and returns a notification message to
    the user.

    Returns
    -------
    a rendered HTML template for the login page with a notification message indicating that
    the user has been created successfully and needs to wait for an admin to approve their account.

    """
    password = generate_password_hash(request.form["password"], method="sha256")
    data = {
        "username": request.form["username"],
        "password": password,
        "name": request.form["name"],
        "last_name": request.form["last_name"],
        "approved": 0,
    }

    signup_db = CrudDB(ZPLATIPLD_URL_DB)
    signup_db.create(Users, data=data)

    return render_template(
        LOGIN_HTML,
        notification=(
            "success",
            "User created successfully. Please wait for an admin to approve your account.",
        ),
    )


@app.route("/vault/ssh", methods=["GET"])
@login_required
def vault_ssh_keys():
    """This function retrieves SSH keys from a database and renders them in an HTML template.

    Returns
    -------
    The function `vault_ssh_keys()` is returning a rendered HTML template with the results of a
    database query for SSH keys stored in a key vault database. The results include
    the ID, username, private key, and public key for each key stored in the database.

    """
    key_vault_database = CrudDB(ZPLATIPLD_URL_DB)
    keys_from_db = key_vault_database.read(Vault)

    return render_template(VAULT_SSH_HTML, results=keys_from_db)


@app.route("/vault/ssh/save", methods=["POST"])
@login_required
def vault_ssh_keys_save():
    """This function saves SSH keys to a database and returns a notification of success or failure.

    Returns
    -------
    a rendered HTML template with a notification message and a result. The notification message
    is a tuple containing a string indicating the type of notification (e.g. "success" or "danger")
    and a message to display. The result is a list of dictionaries containing
    the ID, username, private key, and public key of all SSH keys stored in the key_vault database.

    """
    data = {
        "username": request.form["username"],
        "private_key": request.form["private_key"],
        "public_key": request.form["public_key"],
    }
    try:
        key_vault_database = CrudDB(ZPLATIPLD_URL_DB)
        key_vault_database.create(Vault, data=data)

        return redirect(
            url_for(
                "/vault/ssh",
                notification=(
                    "success",
                    f"The SSH keys was successfully imported for user {request.form['username']}.",
                ),
            )
        )
    except Exception as error:
        return render_template(
            VAULT_SSH_HTML,
            notification=(
                "danger",
                f"An error occurred while importing SSH Keys for "
                f"user {request.form['username']} . [{error}]",
            ),
        )


@app.route("/lpar/tasks", methods=["GET"])
@login_required
def lpar_tasks():
    """This function retrieves enabled LPARs from a database and renders them in an HTML template.

    Returns
    -------
    The function `lpar_tasks()` is returning a rendered HTML template called "lpar_tasks.html"
    with the results of a database query. The query selects specific columns from the "lpar" table
    in the "ipld_db_lpar.db" database where the "enabled" column is equal to 1. The results of
    the query are passed to the template as a variable called "results".

    """
    lpar_database = CrudDB(ZPLATIPLD_URL_DB)
    lpars_from_db = lpar_database.read(Lpar, condition={"enable": 1})

    return render_template("lpar_tasks.html", results=lpars_from_db)


@app.route("/lpar/tasks/run", methods=["POST"])
@app.route("/lpar/tasks/run/<int:id>", methods=["GET"])
@login_required
def lpar_tasks_run(id=None):
    """This function runs a deployment execution for a given set of identifiers either through
    a POST request or a GET request with an optional identifier parameter.

    Parameters
    ----------
    id
    The "id" parameter is an optional integer value that can be passed to the "lpar_tasks_run"
    function. If it is provided, the function will execute a deployment task for the specified
    identifier. If it is not provided, the function will wait for a POST request containing
    a list of identifiers

    Returns
    -------
    the rendered HTML template "lpar_tasks_run.html" after starting a new thread to execute the
    "deploy_execution" function with the given arguments. If the request method is POST,
    the function expects to receive a list of identifiers from the form data and passes them as
    arguments to the "deploy_execution" function.
    """
    if request.method == "POST":
        identifiers = tuple(map(int, request.form.getlist("identifier[]")))
        tasks_run = Thread(target=deploy_execution, args=(*identifiers,))
        tasks_run.start()
        return render_template("lpar_tasks_run.html")
    elif request.method == "GET":
        identifiers = (id, 0)
        tasks_run = Thread(target=deploy_execution, args=(*identifiers,))
        tasks_run.start()
        return render_template("lpar_tasks_run.html")


@app.route("/scheduler/list", methods=["GET"])
# @app.route("/scheduler/list/<string:action>")
@login_required
def scheduler_list():
    schedules_result = []
    active_schedule = schedule.get_jobs()
    for act_sc in active_schedule:
        schedules_result.append(
            {
                "lpar": act_sc.tags,
                "task": act_sc,
                "last_run": act_sc.last_run,
                "next_run": act_sc.next_run,
                "unit": act_sc.unit,
                "interval": act_sc.interval,
                "period": act_sc.period,
            }
        )
    return render_template("scheduler_list.html", results=schedules_result)


@app.route("/lpar/settings", methods=["GET"])
@login_required
def lpar_settings():
    """This function retrieves data from a database and renders it in a template for LPAR settings.

    Returns
    -------
    The function `lpar_settings()` is returning a rendered HTML template called
    "lpar_settings.html" with the results of a database query for a list of LPARs
    and their associated settings. The results are passed to the template as a variable
    called "results".

    """
    lpar_database = CrudDB(ZPLATIPLD_URL_DB)
    lpars_from_db = lpar_database.read(Lpar)
    return render_template(LPAR_SETTINGS_HTML, results=lpars_from_db)


@app.route("/lpar/settings/dry-run", methods=["POST"])
@login_required
async def lpar_settings_dry_run():
    thread_run = Thread(
        target=dry_run_execution,
        args=(
            request.form["hostname"],
            request.form["user_id"],
            request.form["dataset"],
        ),
    )
    thread_run.start()

    return 0


@app.route("/lpar/settings/new/step-1", methods=["GET"])
@login_required
def lpar_settings_new():
    """This function retrieves data from a database and renders it in a template for LPAR settings.

    Returns
    -------
    The function `lpar_settings()` is returning a rendered HTML template called
    "lpar_settings.html" with the results of a database query for a list of LPARs
    and their associated settings. The results are passed to the template as a variable
    called "results".

    """
    lpar_database = CrudDB(ZPLATIPLD_URL_DB)
    lpars_from_db = lpar_database.read(Lpar)

    return render_template("lpar_settings_new.html", results=lpars_from_db)


@app.route("/lpar/settings/new/step-2", methods=["POST"])
@login_required
async def lpar_settings_new_step2():
    thread_run = Thread(
        target=dry_run_execution,
        args=(
            request.form["hostname"],
            request.form["user_id"],
            request.form["dataset"],
        ),
    )
    thread_run.start()

    field_list = {
        "lpar": request.form["lpar"],
        "hostname": request.form["hostname"],
        "dataset": request.form["dataset"],
        "user_id": request.form["user_id"],
    }

    print(field_list)
    return render_template("lpar_settings_new_step2.html", results=field_list)


@app.route("/lpar/settings/new", methods=["POST"])
@login_required
def lpar_settings_insert():
    """This function inserts LPAR settings into a database and returns a success or
        error notification.

    Returns
    -------
    a rendered HTML template with a notification message. If the try block is successful,
    it returns a success notification message with the name of the LPAR that was created. If
    there is an exception, it returns a danger notification message with the name of the LPAR
    that failed to be created and the error message.

    """
    LPAR = request.form["lpar"]
    HOSTNAME = request.form["hostname"]
    DATASET = request.form["dataset"]
    USER_ID = request.form["user_id"]

    try:
        lpar_database = CrudDB(ZPLATIPLD_URL_DB)
        check_lpar_before_insert = lpar_database.read(
            Lpar, condition={"hostname": HOSTNAME}
        )

        if check_lpar_before_insert:
            return render_template(
                LPAR_SETTINGS_HTML,
                notification=(
                    "danger",
                    f"The LPAR {LPAR} already exists. Please provide a unique LPAR.",
                ),
            )
        else:
            data = {
                "lpar": LPAR,
                "hostname": HOSTNAME,
                "dataset": DATASET,
                "username": USER_ID,
                "enable": 1,
            }
            lpar_database.create(Lpar, data=data)

            return render_template(
                LPAR_SETTINGS_HTML,
                notification=(
                    "success",
                    f"The LPAR {LPAR} was created successfully.",
                ),
            )
    except Exception as error:
        return render_template(
            LPAR_SETTINGS_HTML,
            notification=(
                "danger",
                f"An error occurred while creating the LPAR {LPAR}  settings. [{error}]",
            ),
        )


@app.route("/lpar/settings/<int:id>", methods=["GET"])
@login_required
def lpar_settings_detail(id):
    """This function retrieves details of a specific LPAR from a database and renders them in
    an HTML template.

    Parameters
    ----------
    id
    The `id` parameter is an integer value that is used to identify a specific LPAR
    in the database. The function `lpar_settings_detail` retrieves the details of the LPAR with the
    given `id` from the database and returns them to the template `lpar_settings

    Returns
    -------
    The function `lpar_settings_detail` returns the rendered template "lpar_settings_detail.html"
    with the results of a database query for a specific LPAR identified by the `id` parameter.
    The results include the LPAR name, hostname, dataset, username, enabled status, and ID.

    """
    lpar_database = CrudDB(ZPLATIPLD_URL_DB)
    lpars_from_db = lpar_database.read(Lpar, condition={"id": id})

    return render_template(LPAR_SETTINGS_DET_HTML, results=lpars_from_db)


@app.route("/lpar/settings/update/<int:id>", methods=["POST"])
@login_required
def lpar_settings_update(id):
    """This function updates the settings of an LPAR in a database and returns a notification
    of success or failure.

    Parameters
    ----------
    id
    The `id` parameter is an identifier used to specify which LPAR configuration to update in the
    database. It is used in the `condition` parameter of the `select` and `update` methods of the
    `Database` class to retrieve and modify the correct record.

    Returns
    -------
    a rendered HTML template with the updated LPAR configuration details and a notification message
    indicating whether the update was successful or not.

    """
    fields_to_query = {
        "lpar": request.form["lpar"],
        "hostname": request.form["hostname"],
        "dataset": request.form["dataset"],
        "username": request.form["username"],
        "enabled": request.form["enabled"],
        "schedule": request.form["schedule"],
    }
    lpar_database = CrudDB(ZPLATIPLD_URL_DB)
    lpars_from_db = lpar_database.update(Lpar, {"id": id}, fields_to_query)

    try:
        lpar_database.update("lpar", record_id={"id": id}, data=fields_to_query)
        return render_template(
            LPAR_SETTINGS_DET_HTML,
            results=lpars_from_db,
            notification=(
                "success",
                f"The LPAR {request.form['lpar']} configuration has been updated successfully.",
            ),
        )
    except Exception as error:
        return render_template(
            LPAR_SETTINGS_DET_HTML,
            results=lpars_from_db,
            notification=(
                "danger",
                f"An error occurred while updating the LPAR {request.form['lpar']} "
                f"settings. [{error}]",
            ),
        )


@app.route("/lpar/reports", methods=["GET"])
@login_required
def lpar_results_show_dir():
    """This function lists the files in a directory and renders them in an HTML template.

    Returns
    -------
    a rendered HTML template called "lpar_results.html" with the variables "files", "dir_path",
    "os", and "root_dir" passed as arguments. The "files" variable contains a list of files in
    the directory "/zplatipld/results". The "dir_path" variable is an empty string. The "os"
    variable is the Python built-in module

    """

    files = os.listdir(ROOT_RESULTS)
    return render_template(
        "lpar_results.html",
        files=files,
        dir_path="",
        os=os,
        root_dir=ROOT_RESULTS,
    )


@app.route("/lpar/reports/<path:dir_path>", methods=["GET"])
@login_required
def lpar_results_show_dir_dynamic(dir_path=""):
    """This function lists the files in a directory and renders them in an HTML template.

    Parameters
    ----------
    dir_path
    dir_path is a string parameter that represents the path of a directory. It is an optional
    parameter with a default value of an empty string. If a value is provided for dir_path,
    the function will look for files in the specified directory path. If no value is provided,
    the function will look for

    Returns
    -------
    a rendered HTML template with the list of files in the specified directory path, along with the
    directory path, root directory, and the os module.

    """

    safe_base_path = os.path.abspath(ROOT_RESULTS)
    requested_path = os.path.abspath(os.path.join(safe_base_path, dir_path))

    if not requested_path.startswith(safe_base_path):
        abort(403, description="Access denied.")

    if not os.path.isdir(requested_path):
        abort(404, description="Not found")

    try:
        files = os.listdir(requested_path)
    except OSError as error:
        abort(500, description=f"Error accessing the direcotry: {error}")

    return render_template(
        "lpar_results.html",
        files=files,
        dir_path=dir_path,
        os=os,
        root_dir=ROOT_RESULTS,
    )


@app.route("/lpar/reports/download/<path:file_path>", methods=["GET"])
@login_required
def lpar_results_download_file(file_path):
    """This function downloads a file from a specified directory and returns an error message if
    the file is not found.

    Parameters
    ----------
    file_path
    The file path is a string that represents the path to a file that needs to be downloaded. It is
    used to construct the full path to the file by joining it with the root directory path.

    Returns
    -------
    a file for download if it exists at the specified file path. If the file does not exist, it
    will flash an error message and redirect to a directory listing page.

    """

    print("AQUI: ", ROOT_RESULTS)
    print("\n\nAQUI2: ", file_path)
    if os.path.isfile(f"{ROOT_RESULTS}/{file_path}"):
        return send_from_directory(ROOT_RESULTS, file_path)
    flash("Error: File not found")
    return redirect(url_for("lpar_results_show_dir"))


@app.route("/lpar/results/<string:view>", methods=["GET"])
@login_required
def lpar_results_table(view):
    import datetime

    # Running Ingest Data Before
    system_to_duration_ingest = zplatipld_ingest()
    if system_to_duration_ingest:
        system_to_duration_ingest_uncompressed = []
        for uncompress_list in system_to_duration_ingest:
            system_to_duration_ingest_uncompressed.append(uncompress_list[0])
        system_to_duration_ingest_uncompressed = list(
            set(system_to_duration_ingest_uncompressed)
        )
        duration_ingest(system_to_duration_ingest_uncompressed)

    if view == "done":
        done_db = CrudDB(ZPLATIPLD_URL_DB)
        load_done_results = done_db.read(ResultsDoneTable)

        results = []
        for result in load_done_results:
            result_to_dict = {
                "id": result.id,
                "sysname": result.sysname,
                "ipl_date": result.ipl_date,
                "log_dataset": result.log_dataset,
                "pre_ipl": result.pre_ipl,
                "shutdown_begin": result.shutdown_begin,
                "shutdown_end": result.shutdown_end,
                "ipl_begin": result.ipl_begin,
                "ipl_end": result.ipl_end,
                "pos_ipl": result.pos_ipl,
                "shutdown_duration": result.shutdown_duration,
                "poweroff_duration": result.poweroff_duration,
                "load_ipl": result.load_ipl,
                "total_duration": result.total_duration,
            }
            results.append(result_to_dict)

        return render_template(
            "lpar_results_table.html",
            datetime=datetime,
            results=results,
        )
    elif view == "fail":
        fail_db = CrudDB(ZPLATIPLD_URL_DB)
        load_done_results = fail_db.read(ResultsFailTable)

        results = []
        for result in load_done_results:
            result_to_dict = {
                "id": result.id,
                "sysname": result.sysname,
                "log_dataset": result.log_dataset,
                "pre_ipl": result.pre_ipl,
                "shutdown_begin": result.shutdown_begin,
                "shutdown_end": result.shutdown_end,
                "ipl_begin": result.ipl_begin,
                "ipl_end": result.ipl_end,
                "pos_ipl": result.pos_ipl,
            }
            results.append(result_to_dict)

        return render_template(
            "lpar_results_table_fail.html",
            results=results,
        )
    elif view == "last_ipl":
        last_ipl_db = CrudDB(ZPLATIPLD_URL_DB)
        load_done_results = last_ipl_db.read(
            (ResultsLastIplTable),
            distinct="sysname,last_ipl",
        )

        results = []
        for result in load_done_results:
            result_to_dict = {
                "sysname": result.sysname,
                "last_ipl": result.last_ipl,
            }
            results.append(result_to_dict)

        return render_template(
            "lpar_results_table_last_ipl.html",
            results=results,
        )


@app.route("/people/access/approve", methods=["GET"])
@login_required
def people_access_approve():
    """This function retrieves data from a database and renders it in a template
     for approving people's access.

    Returns
    -------
    a rendered HTML template called "people_access_approve.html" with the
    results of a database query for user information including username, name,
    last name, approval status, and ID.

    """
    people_db = CrudDB(ZPLATIPLD_URL_DB)
    people = people_db.read(Users)

    results = []
    for register in people:
        results.append(
            {
                "username": register.username,
                "name": register.name,
                "last_name": register.last_name,
                "approved": register.approved,
                "id": register.id,
            }
        )

    return render_template("people_access_approve.html", results=results)


@app.route(
    "/people/access/approve/action/<string:action>/<int:id>", methods=["GET"]
)
@login_required
def people_access_approve_action(action, id):
    """This function updates the "approved" field of a user in a database based on the given action
    and ID, and then redirects to a specific page.

    Parameters
    ----------
    action
    The action parameter is a string that specifies the action to be taken. It can be either
    "unblock" or any other string.

    id
    The "id" parameter is likely an identifier for a specific user in a database. It is used
    to update the "approved" field for that user in the "user" table of the "ipld_db_user.db"
    database. The function either sets the "approved" field to 1.

    Returns
    -------
        a redirect to the "/people/access/approve" page.

    """
    if action == "unblock":
        people_access_db = CrudDB(ZPLATIPLD_URL_DB)
        data = {"approved": 1}
        register_id = {"id": id}
        people_access_db.update(Users, register_id, data=data)
    else:
        people_access_db = CrudDB(ZPLATIPLD_URL_DB)
        data = {"approved": 0}
        register_id = {"id": id}
        people_access_db.update(Users, register_id, data=data)

    return redirect("/people/access/approve")


@app.route("/system/database/import", methods=["GET"])
@app.route("/system/database/import/<string:action>", methods=["POST"])
@login_required
def import_database(action=None):
    if not action:
        return render_template("system_database_import.html")
    elif action == "add":
        import json

        lpar_database = CrudDB(ZPLATIPLD_URL_DB)
        table = request.form["table"]
        data_to_import = request.form["data_to_import"]
        data_to_json = json.dumps(data_to_import)
        json_loads_data = json.loads(data_to_json)
        teste = jsonify(json_loads_data)
        print(teste)
        # for data in data_to_import.split(","):
        #     # lpar_database.create(Lpar,data)
        #     dict_data = ast.literal_eval(data)
        #     print(dict_data.get("lpar"))
        lpars_result = lpar_database.read(Lpar)
        # return render_template(LPAR_SETTINGS_HTML,results=lpars_result)
        return json_loads_data


host_env = os.getenv("HOST")
port_env = os.getenv("PORT")
debug_env = os.getenv("DEBUG")


if __name__ == "__main__":
    # teste
    db_init = CrudDB(ZPLATIPLD_URL_DB)
    db_init.init_database()
    schedule_thread_run = Thread(target=task_scheduler_manager, daemon=True)
    schedule_thread_run.start()
    socketio.run(
        app,
        allow_unsafe_werkzeug=True,
        host="0.0.0.0",
        port=5000,
        debug=True,
    )
