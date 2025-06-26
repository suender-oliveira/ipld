"""
Contains authentication-related functionality for the application's API.
"""

from collections.abc import Callable

from flask import (
    Blueprint,
    Response,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import UserMixin, login_required, login_user, logout_user

from app.application.dtos import (
    UserApprovalActionDTO,
    UserCreateDTO,
    UserLoginDTO,
)
from app.application.services.auth_service import AuthService


class FlaskLoginUser(UserMixin):
    """
    A class representing a user in the Flask-Login system.
    """

    def __init__(self, user_id: int, username: str, approved: int) -> None:
        self.id = user_id
        self.username = username
        self.approved = approved

    def get_id(self) -> str:
        """
        Returns the ID of the object as a string.

        Parameters:
        self (class instance): The instance of the class calling the method.

        Returns:
        str: The ID of the object as a string.
        """

        return str(self.id)

    @property
    def is_active(self) -> bool:
        """
        Check if the user account is active.

        Args:
            None

        Returns:
            bool: True if the user account is active, False otherwise.
        """

        return self.approved == 1

    def is_authenticated(self) -> bool:
        """
        Check if the user is authenticated.

        Args:
            None

        Returns:
            bool: True if the user is authenticated, False otherwise.
        """

        return True

    def is_anonymous(self) -> bool:
        """
        Check if the user is anonymous.

        Args:
            self (class instance): The class instance on which the method is
                called.

        Returns:
            bool: True if the user is anonymous, False otherwise.
        """

        return False


def create_auth_blueprint(
    auth_service: AuthService, login_manager_init_app: Callable
) -> Blueprint:
    """Creates a Flask blueprint for handling user authentication.

    Args:
        auth_service (AuthService): An instance of the AuthService class.
        login_manager_init_app (Callable): A function that initializes
            the Flask-Login extension.

    Returns:
        Blueprint: The created Flask blueprint.
    """

    auth_bp = Blueprint("auth_bp", __name__)

    # Configure Flask-Login user loader
    @login_manager_init_app
    def load_user(user_id: str) -> FlaskLoginUser | None:
        """Loads a user from the database based on their ID.

        Args:
            user_id (str): The ID of the user to load.

        Returns:
            FlaskLoginUser | None: The loaded user object, or None if
                the user could not be loaded.

        Raises:
            Exception: If an error occurs while loading the user.
        """

        try:
            domain_user = auth_service.get_user_by_id(int(user_id))
            if domain_user:
                return FlaskLoginUser(
                    domain_user.id, domain_user.username, domain_user.approved
                )
        except Exception as e:
            print(f"Error loading user: {e}")
        else:
            return None

    @auth_bp.route("/login", methods=["GET", "POST"])
    def login() -> str | Response:
        """
        Handle user login.

        Args:
            None

        Returns:
            str: The rendered "login.html" template if the request method
                is GET.
            str: A success message and a redirect to the main page if
                the login is successful.
            str: A warning message and a redirect to the login page if
                the account is pending approval.
            str: An error message and a redirect to the login page if
                the username or password is invalid.
        """
        if request.method == "GET":
            return render_template("login.html")
        username = request.form["username"]
        password = request.form["password"]
        login_dto = UserLoginDTO(username=username, password=password)
        authenticated_user = auth_service.verify_login(login_dto)
        if authenticated_user and authenticated_user.approved == 1:
            flask_user = FlaskLoginUser(
                authenticated_user.id,
                authenticated_user.username,
                authenticated_user.approved,
            )
            login_user(flask_user)
            session["approved"] = authenticated_user.approved
            flash("Logged in successfully!", "success")
            return redirect(url_for("main_bp.index"))
        if authenticated_user and authenticated_user.approved == 0:
            flash(
                "Your account is pending approval. Please wait for an admin.",
                "warning",
            )
            return render_template("login.html")
        flash("Invalid username or password.", "danger")
        return render_template("login.html")

    @auth_bp.route("/logout", methods=["GET"])
    @login_required
    def logout() -> Response:
        """Logs out the current user and redirects them to the login page.

        Args:
            None

        Returns:
            Redirects to the login page.
        """

        logout_user()
        flash("You have been logged out.", "info")
        return redirect(url_for("auth_bp.login"))

    @auth_bp.route("/signup", methods=["GET"])
    def signup_form() -> str:
        """
        Renders the signup form HTML template.

        Args:
            None

        Returns:
            str: The rendered HTML template for the signup form.
        """

        return render_template("signup.html")

    @auth_bp.route("/signup/save", methods=["POST"])
    def signup_save() -> str:
        """Register a new user account.

        Args:
            username (str): The username for the new account.
            password (str): The password for the new account.
            name (str): The first name of the user.
            last_name (str): The last name of the user.

        Returns:
            str: A success message if the account was created successfully,
                or an error message if there was an issue.
        """

        username = request.form["username"]
        password = request.form["password"]
        name = request.form["name"]
        last_name = request.form["last_name"]
        signup_dto = UserCreateDTO(
            username=username,
            password=password,
            name=name,
            last_name=last_name,
        )
        try:
            auth_service.register_user(signup_dto)
            flash(
                "User created successfully. Please wait for an admin to "
                "approve your account.",
                "success",
            )
            return redirect(url_for("auth_bp.login"))
        except Exception as e:
            flash(f"An error occurred during signup: {e}", "danger")
            return render_template("signup.html")

    @auth_bp.route("/people/access/approve", methods=["GET"])
    @login_required
    def people_access_approve() -> list[dict]:
        """
        Returns a list of users with their details.

        Parameters:
        None

        Returns:
        List[dict]: A list of dictionaries containing user details.
        Each dictionary contains the following keys:
            id (int): The unique identifier of the user.
            username (str): The username of the user.
            name (str): The first name of the user.
            last_name (str): The last name of the user.
            approved (bool): Whether the user's access has been approved
                or not.
        """

        users = auth_service.get_all_users()

        results = [
            {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "last_name": user.last_name,
                "approved": user.approved,
            }
            for user in users
        ]
        return render_template("people_access_approve.html", results=results)

    @auth_bp.route(
        "/people/access/approve/action/<string:action>/<int:id>",
        methods=["GET"],
    )
    @login_required
    def people_access_approve_action(action: str, id: int) -> Response:
        """
        Approve or reject access for a user.

        Args:
            action (str): The action to take ("approve" or "reject").
            id (int): The ID of the user to approve or reject access for.

        Returns:
            Response: A Flask response object.

        Raises:
            ValueError: If the action is not either "approve" or "reject".
        """

        action_dto = UserApprovalActionDTO(user_id=id, action=action)
        updated_user = auth_service.update_user_approval(action_dto)
        if updated_user:
            flash(
                f"User {updated_user.username} approval status "
                f"updated to {action}.",
                "success",
            )
        else:
            flash(f"Failed to update approval for user ID {id}.", "danger")
        return redirect(url_for("auth_bp.people_access_approve"))

    return auth_bp
