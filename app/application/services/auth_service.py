"""
Provides services related to user authentication.

Classes:
    AuthService: Handles user registration, login, and approval status updates.
"""

from app.application.dtos import (
    UserApprovalActionDTO,
    UserCreateDTO,
    UserLoginDTO,
)
from app.domain.entities import User
from app.domain.repositories import IUserRepository
from app.domain.services import IPasswordHasher
from app.infrastructure.persistence.models import UserModel


class AuthService:
    """
    Handles user authentication-related operations.
    """

    def __init__(
        self, user_repo: IUserRepository, password_hasher: IPasswordHasher
    ) -> None:
        """
        Initializes the UserManager class.

        Args:
            user_repo (IUserRepository): The repository for storing and
                retrieving user data.
            password_hasher (IPasswordHasher): The hasher for hashing
                passwords.

        Returns:
            None
        """

        self.user_repo = user_repo
        self.password_hasher = password_hasher

    def register_user(self, dto: UserCreateDTO) -> User | None:
        """Register a new user.

        Args:
            dto (UserCreateDTO): The data transfer object containing
                the user's information.

        Returns:
            User | None: The created user or None if the registration failed.
        """

        hashed_password = self.password_hasher.hash_password(dto.password)
        new_user = User(
            id=None,
            username=dto.username,
            password=hashed_password,
            name=dto.name,
            last_name=dto.last_name,
            approved=0,
        )
        return self.user_repo.create(new_user)

    def verify_login(self, dto: UserLoginDTO) -> User | None:
        """
        Verify a user's login credentials.

        Parameters:
            dto (UserLoginDTO): A data transfer object containing
                the username and password.

        Returns:
            User | None: The verified user object if successful, or
                None if the login failed.
        """

        users = self.user_repo.get_by_username(username=dto.username)
        if not users:
            return None

        user = users[0]
        if self.password_hasher.check_password(dto.password, user.password):
            return user
        return None

    def get_user_by_id(self, user_id: int) -> User | None:
        """
        Returns a User object from the database based on the provided user ID.

        Parameters:
            user_id (int): The unique identifier of the User to retrieve.

        Returns:
            User | None: The retrieved User object if found, otherwise None.
        """
        return self.user_repo.get_by_id(user_id)

    def get_all_users(self) -> list[User]:
        """
        Returns a list of all users in the system.

        Parameters:
        self (class instance): The instance of the class calling the method.

        Returns:
        list[User]: A list of User objects representing all users in
            the system.
        """

        return self.user_repo.get_all()

    def update_user_approval(self, dto: UserApprovalActionDTO) -> User | None:
        """
        Updates the approval status of a user based on the provided DTO.

        Parameters:
            - dto (UserApprovalActionDTO): A data transfer object containing
                the user ID and action to be performed.

        Returns:
            - User | None: The updated user object if successful, or None if
                the user was not found.
        """

        user_to_update = self.user_repo.get_by_id(dto.user_id)
        if not user_to_update:
            return None

        user_to_update.approved = 1 if dto.action == "unblock" else 0
        return self.user_repo.update(user_to_update)
