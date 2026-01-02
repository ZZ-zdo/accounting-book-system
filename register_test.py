import pytest
import os
from main18 import Database

@pytest.fixture(scope="function")  # ✅ 每个测试函数独立
#@pytest.fixture(scope="module")
def db():
    """为每个测试创建干净的数据库环境"""
    test_db_name = "test_accounting.db"
    
    # 删除旧的测试数据库文件（如果存在）
    if os.path.exists(test_db_name):
        os.remove(test_db_name)
    
    # 创建新的数据库
    db = Database(db_name=test_db_name)
    db.init_database()
    
    yield db
    
    # 测试结束后清理
    if os.path.exists(test_db_name):
        os.remove(test_db_name)


@pytest.fixture(scope="function")
#@pytest.fixture(scope="module")
def db_with_user():
    """创建带有预置用户的数据库（用于测试用户名重复等场景）"""
    test_db_name = "test_accounting_with_user.db"
    
    if os.path.exists(test_db_name):
        os.remove(test_db_name)
    
    db = Database(db_name=test_db_name)
    db.init_database()
    
    # 预先创建测试用户
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", 
                   ("testuser", "hashed_password"))
    conn.commit()
    cursor.execute("INSERT INTO accounts (user_id, account_name, initial_balance, current_balance) VALUES (?, ?, ?, ?)",
                   (1, "test_account", 1000, 1000))
    conn.commit()
    conn.close()
    
    yield db
    
    if os.path.exists(test_db_name):
        os.remove(test_db_name)


# ============ 测试用例 ============

def test_register_user_success(db):
    """测试：成功注册新用户"""
    result, user_id = db.register_user("test_user", "password123")
    assert result is True
    assert user_id is not None
    assert isinstance(user_id, int)


def test_register_user_username_exists(db_with_user):
    """测试：用户名已存在"""
    # 使用 db_with_user，它已经有 "testuser"
    result, message = db_with_user.register_user("test_user", "password123")
    assert result is False
    assert "用户名" in str(message) or "exist" in str(message).lower()


def test_register_user_empty_password(db):
    """测试：空密码应该失败"""
    result, message = db.register_user("newuser", "")
    assert result is False
    # ✅ 修复：失败时不检查 user_id


def test_register_user_empty_username(db):
    """测试：空用户名应该失败"""
    result, message = db.register_user("", "password123")
    assert result is False
    # ✅ 修复：失败时不检查 user_id


def test_register_user_with_phone(db):
    """测试：注册时提供手机号"""
    result, user_id = db.register_user("phoneuser", "password123", "1234567890")
    assert result is True
    assert user_id is not None


def test_register_user_with_special_characters(db):
    """测试：用户名包含特殊字符"""
    result, user_id = db.register_user("user@123", "password123")
    assert result is True
    assert user_id is not None


def test_register_user_with_minimum_length_username(db):
    """测试：单字符用户名"""
    result, user_id = db.register_user("a", "password123")
    assert result is True
    assert user_id is not None


def test_register_user_with_very_long_username(db):
    """测试：超长用户名"""
    long_username = "a" * 256
    result, message = db.register_user(long_username, "password123")
    assert result is False
    # ✅ 修复：失败时不检查 user_id


def test_register_user_with_very_long_password(db):
    """测试：超长密码"""
    long_password = "a" * 256
    result, response = db.register_user("newuser", long_password)
    assert result is False
    # 根据实际实现，可能成功也可能失败
    # if result:
    #     assert response is not None  # user_id
    # else:
    #     assert "密码" in str(response) or "password" in str(response).lower()


def test_register_user_with_phone_format(db):
    """测试：特殊格式的手机号"""
    result, user_id = db. register_user("newphoneuser", "password123", "123-456-7890")
    assert result is False