from typing import List
from app.repositories.user_repo import UserRepository
from app.repositories.log_repo import LogRepository
from app.models.user import User

class UserService:
    def __init__(self, repo: UserRepository, log_repo: LogRepository):
        self.repo = repo
        self.log_repo = log_repo

    def get_all_users(self) -> List[User]:
        return self.repo.fetch_all_users()

    def add_user(self, user: User) -> bool:
        if self.repo.add_user(user):
            self.log_repo.add_log("info", f"ユーザー追加: {user.name}")
            return True
        return False

    def update_user(self, user: User) -> bool:
        # 更新前の名前などがわかればログに出せるが、ここではシンプルに実装
        if self.repo.update_user(user):
            self.log_repo.add_log("info", f"ユーザー更新: {user.name}")
            return True
        return False

    def delete_user(self, user: User) -> bool:
        if self.repo.delete_user(user.id):
            self.log_repo.add_log("warning", f"ユーザー完全削除: {user.name}")
            return True
        return False

    def disable_user(self, user: User) -> bool:
        user.is_active = False
        if self.repo.update_user(user):
            self.log_repo.add_log("info", f"ユーザー無効化: {user.name}")
            return True
        return False