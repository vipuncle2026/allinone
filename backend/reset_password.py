"""密码重置工具 - 无需登录，直接重置用户密码

用法：
  python reset_password.py                # 重置 admin 密码为 admin
  python reset_password.py admin           # 重置指定用户密码为 admin
  python reset_password.py admin 123456    # 重置指定用户密码为 123456
"""
import sys
import os

# 确保能找到同目录的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hashlib
from database import get_session_factory


def reset_password(username: str, new_password: str):
    db = get_session_factory()()
    try:
        from models.auth import User
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"错误：用户 '{username}' 不存在")
            return False

        password_hash = hashlib.sha256(f"aio_salt_{new_password}".encode()).hexdigest()
        user.password_hash = password_hash
        db.commit()
        print(f"用户 '{username}' 的密码已重置为：{new_password}")
        return True
    finally:
        db.close()


if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "admin"
    new_password = sys.argv[2] if len(sys.argv) > 2 else "admin"
    reset_password(username, new_password)
