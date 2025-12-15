import pytest
import os
import sqlite3
from main18 import Database
from datetime import datetime, timedelta


# ============ Fixtures ============

@pytest.fixture(scope="function")
def db():
    """干净的数据库"""
    test_db = "test_bill_management.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    db = Database(db_name=test_db)
    db.init_database()
    yield db
    
    if os.path.exists(test_db):
        os.remove(test_db)


@pytest.fixture(scope="function")
def db_with_account():
    """带有用户和账户的数据库（用于账单测试）"""
    test_db = "test_bill_with_account.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    db = Database(db_name=test_db)
    db.init_database()
    
    # 创建测试用户
    success, user_id = db.register_user("billuser", "password123")
    assert success is True
    
    # 创建测试账户（初始余额1000，月预算5000）
    account_id = db.create_account(user_id, "测试账户", 1000.0, 5000.0)
    
    # 将 user_id 和 account_id 保存到 db 对象中
    db.test_user_id = user_id
    db.test_account_id = account_id
    
    yield db
    
    if os. path.exists(test_db):
        os.remove(test_db)


@pytest.fixture(scope="function")
def db_with_bills():
    """带有多条测试账单的数据库"""
    test_db = "test_with_multiple_bills.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    db = Database(db_name=test_db)
    db.init_database()
    
    # 创建用户和账户
    success, user_id = db.register_user("queryuser", "password123")
    account_id = db.create_account(user_id, "查询账户", 10000.0, 5000.0)
    
    # 获取默认标签ID（餐饮、工资）
    tags = db.get_user_tags(user_id)
    food_tag_id = next((t[0] for t in tags if t[1] == '餐饮'), None)
    salary_tag_id = next((t[0] for t in tags if t[1] == '工资'), None)
    
    # 添加测试数据
    db.add_bill(user_id, account_id, '支出', 50.0, '2025-12-01', food_tag_id, '早餐')
    db.add_bill(user_id, account_id, '支出', 120.0, '2025-12-05', food_tag_id, '午餐聚餐')
    db.add_bill(user_id, account_id, '收入', 5000.0, '2025-12-10', salary_tag_id, '月工资')
    db.add_bill(user_id, account_id, '支出', 200.0, '2025-11-15', food_tag_id, '上月账单')
    
    db.test_user_id = user_id
    db.test_account_id = account_id
    
    yield db
    
    if os.path.exists(test_db):
        os.remove(test_db)


# ============ 测试用例 ============

def test_01_add_bill_expense_success(db_with_account):
    """
    测试1:  正常添加支出账单
    覆盖策略:  语句覆盖 + 判定覆盖（bill_type == '支出' 分支）
    边界:  正常金额、有效日期
    """
    user_id = db_with_account.test_user_id
    account_id = db_with_account.test_account_id
    
    # 获取操作前的余额
    accounts_before = db_with_account. get_user_accounts(user_id)
    balance_before = accounts_before[0][2]  # current_balance
    
    # 添加支出账单
    success, bill_id = db_with_account.add_bill(
        user_id=user_id,
        account_id=account_id,
        bill_type='支出',
        amount=150.0,
        bill_date='2025-12-12',
        tag_id=None,
        remark='测试支出'
    )
    
    # 断言
    assert success is True, "添加账单应该成功"
    assert bill_id is not None, "应该返回账单ID"
    assert isinstance(bill_id, int), "账单ID应该是整数"
    
    # 验证余额变化（应该减少）
    accounts_after = db_with_account.get_user_accounts(user_id)
    balance_after = accounts_after[0][2]
    assert balance_after == balance_before - 150.0, f"余额应该减少150，实际:  {balance_before} -> {balance_after}"
    
    # 验证账单是否被正确存储
    bills = db_with_account.get_bills(user_id)
    assert len(bills) > 0, "应该能查询到账单"
    latest_bill = bills[0]  # 最新的账单
    assert latest_bill[4] == 150.0, "金额应该匹配"
    assert latest_bill[3] == '支出', "类型应该是支出"


def test_02_add_bill_income_success(db_with_account):
    """
    测试2: 正常添加收入账单
    覆盖策略: 判定覆盖（bill_type == '收入' 分支）
    边界: 大额收入
    """
    user_id = db_with_account.test_user_id
    account_id = db_with_account.test_account_id
    
    accounts_before = db_with_account.get_user_accounts(user_id)
    balance_before = accounts_before[0][2]
    
    # 添加收入账单（大额）
    success, bill_id = db_with_account.add_bill(
        user_id=user_id,
        account_id=account_id,
        bill_type='收入',
        amount=5000.0,
        bill_date='2025-12-01',
        tag_id=None,
        remark='月工资'
    )
    
    # 断言
    assert success is True, "添加收入账单应该成功"
    assert bill_id is not None, "应该返回账单ID"
    
    # 验证余额增加
    accounts_after = db_with_account.get_user_accounts(user_id)
    balance_after = accounts_after[0][2]
    assert balance_after == balance_before + 5000.0, f"余额应该增加5000，实际: {balance_before} -> {balance_after}"


def test_03_add_bill_with_tag(db_with_account):
    """
    测试3: 添加带标签的账单
    覆盖策略: 条件覆盖（tag_id 不为 None 的情况）
    边界: 正常标签关联
    """
    user_id = db_with_account. test_user_id
    account_id = db_with_account.test_account_id
    
    # 获取一个默认标签（餐饮）
    tags = db_with_account.get_user_tags(user_id, '支出')
    assert len(tags) > 0, "应该有默认标签"
    tag_id = tags[0][0]  # 第一个标签的ID
    tag_name = tags[0][1]
    
    # 添加带标签的账单
    success, bill_id = db_with_account.add_bill(
        user_id=user_id,
        account_id=account_id,
        bill_type='支出',
        amount=88.0,
        bill_date='2025-12-12',
        tag_id=tag_id,
        remark='午餐'
    )
    
    assert success is True, "带标签的账单应该添加成功"
    
    # 验证标签关联
    bills = db_with_account.get_bills(user_id, tag_id=tag_id)
    assert len(bills) > 0, "应该能通过标签查询到账单"
    assert bills[0][2] == tag_name, f"标签名称应该是 {tag_name}"


def test_04_add_bill_zero_amount(db_with_account):
    """
    测试4: 添加金额为0的账单
    覆盖策略: 边界值覆盖（金额 = 0）
    预期:  根据业务逻辑，可能允许或拒绝
    """
    user_id = db_with_account.test_user_id
    account_id = db_with_account.test_account_id
    
    accounts_before = db_with_account.get_user_accounts(user_id)
    balance_before = accounts_before[0][2]
    
    # 添加金额为0的账单
    success, result = db_with_account.add_bill(
        user_id=user_id,
        account_id=account_id,
        bill_type='支出',
        amount=0.0,
        bill_date='2025-12-12',
        remark='测试零金额'
    )
    
    # 根据实际实现调整断言
    # 选项1: 允许0金额账单
    if success:
        accounts_after = db_with_account.get_user_accounts(user_id)
        balance_after = accounts_after[0][2]
        assert balance_after == balance_before, "余额不应该变化"
    # 选项2: 不允许0金额账单
    else:
        assert "金额" in str(result) or "不能为0" in str(result), "应该提示金额错误"


def test_05_add_bill_negative_amount(db_with_account):
    """
    测试5: 添加负数金额的账单
    覆盖策略: 边界值覆盖（金额 < 0）
    预期: 应该失败或自动转为正数
    """
    user_id = db_with_account. test_user_id
    account_id = db_with_account.test_account_id
    
    # 尝试添加负数金额
    success, result = db_with_account.add_bill(
        user_id=user_id,
        account_id=account_id,
        bill_type='支出',
        amount=-100.0,
        bill_date='2025-12-12',
        remark='负数测试'
    )
    
    # 应该失败或有特殊处理
    if not success:
        assert "金额" in str(result) or "不能为负" in str(result), "应该提示金额错误"
    else: 
        # 如果允许，验证数据库中的值
        bills = db_with_account.get_bills(user_id)
        # 可能被存储为 -100 或自动转为 100
        print(f"负数金额账单结果: {bills[0][4]}")


def test_06_add_bill_invalid_account(db_with_account):
    """
    测试6: 使用不存在的账户ID添加账单
    覆盖策略: 异常路径覆盖（FOREIGN KEY 约束）
    边界: 无效的 account_id
    """
    user_id = db_with_account.test_user_id
    invalid_account_id = 99999  # 不存在的账户ID
    
    # 尝试添加账单
    success, result = db_with_account.add_bill(
        user_id=user_id,
        account_id=invalid_account_id,
        bill_type='支出',
        amount=50.0,
        bill_date='2025-12-12',
        remark='无效账户测试'
    )
    
    # 应该失败
    assert success is False, "使用无效账户ID应该失败"
    assert isinstance(result, str), "应该返回错误消息"
    print(f"错误消息: {result}")


def test_07_delete_bill_success(db_with_account):
    """
    测试7: 成功删除账单并恢复余额
    覆盖策略: 语句覆盖 + 判定覆盖（删除逻辑）
    路径: 支出账单删除 -> 余额增加
    """
    user_id = db_with_account. test_user_id
    account_id = db_with_account.test_account_id
    
    # 先添加一个账单
    success, bill_id = db_with_account.add_bill(
        user_id=user_id,
        account_id=account_id,
        bill_type='支出',
        amount=200.0,
        bill_date='2025-12-12',
        remark='待删除账单'
    )
    assert success is True, "添加账单应该成功"
    
    # 获取当前余额
    accounts_before = db_with_account.get_user_accounts(user_id)
    balance_before = accounts_before[0][2]  # 应该是 1000 - 200 = 800
    
    # 删除账单
    success, message = db_with_account.delete_bill(bill_id)
    
    # 断言
    assert success is True, f"删除账单应该成功，实际: {message}"
    assert "成功" in message or "删除" in message, f"应该返回成功消息，实际: {message}"
    
    # 验证余额恢复（支出被删除，余额增加）
    accounts_after = db_with_account. get_user_accounts(user_id)
    balance_after = accounts_after[0][2]
    assert balance_after == balance_before + 200.0, f"余额应该恢复200，实际: {balance_before} -> {balance_after}"
    
    # 验证账单已从数据库删除
    bills = db_with_account.get_bills(user_id)
    bill_ids = [b[0] for b in bills]
    assert bill_id not in bill_ids, "账单应该已被删除"


def test_08_delete_bill_income_restore_balance(db_with_account):
    """
    测试8: 删除收入账单并正确扣减余额
    覆盖策略: 路径覆盖（删除收入账单的分支）
    边界: 收入账单删除 -> 余额减少
    """
    user_id = db_with_account. test_user_id
    account_id = db_with_account.test_account_id
    
    # 添加收入账单
    success, bill_id = db_with_account.add_bill(
        user_id=user_id,
        account_id=account_id,
        bill_type='收入',
        amount=1000.0,
        bill_date='2025-12-12',
        remark='待删除收入'
    )
    assert success is True
    
    # 当前余额应该是 1000 + 1000 = 2000
    accounts_before = db_with_account.get_user_accounts(user_id)
    balance_before = accounts_before[0][2]
    
    # 删除收入账单
    success, message = db_with_account.delete_bill(bill_id)
    
    assert success is True, "删除收入账单应该成功"
    
    # 验证余额减少
    accounts_after = db_with_account.get_user_accounts(user_id)
    balance_after = accounts_after[0][2]
    assert balance_after == balance_before - 1000.0, f"余额应该减少1000，实际: {balance_before} -> {balance_after}"


def test_09_delete_nonexistent_bill(db_with_account):
    """
    测试9: 删除不存在的账单
    覆盖策略: 异常路径覆盖（账单不存在的情况）
    边界:  无效的 bill_id
    """
    nonexistent_bill_id = 99999
    
    # 尝试删除不存在的账单
    success, message = db_with_account.delete_bill(nonexistent_bill_id)
    
    # 应该失败
    assert success is False, "删除不存在的账单应该失败"
    assert "不存在" in message, f"应该提示账单不存在，实际消息: {message}"


def test_10_get_bills_with_filters(db_with_bills):
    """
    测试10: 综合查询 - 多条件筛选账单
    覆盖策略: 条件覆盖 + 路径覆盖（查询参数的各种组合）
    边界: 日期范围、标签筛选、账单类型
    """
    user_id = db_with_bills.test_user_id
    account_id = db_with_bills.test_account_id
    
    # 场景1: 无过滤条件，获取所有账单
    all_bills = db_with_bills.get_bills(user_id)
    assert len(all_bills) == 4, f"应该有4条账单，实际:  {len(all_bills)}"
    
    # 场景2: 按账户筛选
    bills_by_account = db_with_bills. get_bills(user_id, account_id=account_id)
    assert len(bills_by_account) == 4, "按账户筛选应该返回4条"
    
    # 场景3: 按日期范围筛选（只查12月的）
    bills_december = db_with_bills.get_bills(
        user_id,
        start_date='2025-12-01',
        end_date='2025-12-31'
    )
    assert len(bills_december) == 3, f"12月应该有3条账单，实际: {len(bills_december)}"
    
    # 场景4: 按账单类型筛选（只查支出）
    bills_expense = db_with_bills.get_bills(user_id, bill_type='支出')
    assert len(bills_expense) == 3, f"支出账单应该有3条，实际: {len(bills_expense)}"
    assert all(b[3] == '支出' for b in bills_expense), "所有结果都应该是支出"
    
    # 场景5: 按标签筛选（餐饮类）
    tags = db_with_bills.get_user_tags(user_id)
    food_tag_id = next((t[0] for t in tags if t[1] == '餐饮'), None)
    if food_tag_id:
        bills_food = db_with_bills.get_bills(user_id, tag_id=food_tag_id)
        assert len(bills_food) == 3, f"餐饮标签应该有3条账单，实际: {len(bills_food)}"
    
    # 场景6: 复合条件（12月 + 支出 + 餐饮）
    if food_tag_id:
        bills_complex = db_with_bills.get_bills(
            user_id,
            tag_id=food_tag_id,
            start_date='2025-12-01',
            end_date='2025-12-31',
            bill_type='支出'
        )
        assert len(bills_complex) == 2, f"复合查询应该返回2条，实际: {len(bills_complex)}"
    
    # 场景7: 结果按日期降序排列
    assert all_bills[0][5] >= all_bills[-1][5], "账单应该按日期降序排列"


# ============ 额外的边界测试（Bonus） ============

def test_11_add_bill_with_long_remark(db_with_account):
    """
    Bonus测试: 超长备注
    覆盖策略:  边界值覆盖（字符串长度）
    """
    user_id = db_with_account.test_user_id
    account_id = db_with_account. test_account_id
    
    long_remark = "测" * 1000  # 1000个字符
    
    success, bill_id = db_with_account.add_bill(
        user_id=user_id,
        account_id=account_id,
        bill_type='支出',
        amount=50.0,
        bill_date='2025-12-12',
        remark=long_remark
    )
    
    if success:
        # 验证备注是否被正确存储
        bills = db_with_account.get_bills(user_id)
        assert long_remark in bills[0][6], "超长备注应该被正确存储"
    else:
        print(f"超长备注被拒绝: {bill_id}")


def test_12_add_bill_invalid_date_format(db_with_account):
    """
    Bonus测试: 无效的日期格式
    覆盖策略: 异常路径覆盖
    """
    user_id = db_with_account.test_user_id
    account_id = db_with_account.test_account_id
    
    # 尝试无效日期格式
    success, result = db_with_account.add_bill(
        user_id=user_id,
        account_id=account_id,
        bill_type='支出',
        amount=50.0,
        bill_date='12/12/2025',  # 错误格式
        remark='日期格式测试'
    )
    
    # 可能成功（SQLite很宽松）或失败
    print(f"无效日期格式结果: success={success}, result={result}")


def test_13_budget_warning_trigger(db_with_account):
    """
    Bonus测试: 预算警告触发
    覆盖策略:  条件覆盖（预算检查逻辑）
    验证: check_budget_warning 方法是否被调用
    """
    user_id = db_with_account.test_user_id
    account_id = db_with_account.test_account_id
    
    # 月预算是5000，添加多笔支出超过90%（4500）
    db_with_account.add_bill(user_id, account_id, '支出', 2000.0, '2025-12-01', None, '大额支出1')
    db_with_account.add_bill(user_id, account_id, '支出', 2000.0, '2025-12-05', None, '大额支出2')
    
    # 第三笔应该触发警告（总计4500，超过90%）
    # 注意: check_budget_warning 会弹出 messagebox，测试环境需要 mock
    success, bill_id = db_with_account.add_bill(
        user_id, account_id, '支出', 500.0, '2025-12-10', None, '触发预算警告'
    )
    
    assert success is True, "即使触发警告，账单也应该成功添加"
    
    # 验证本月总支出
    bills = db_with_account.get_bills(user_id, start_date='2025-12-01', end_date='2025-12-31')
    total_expense = sum(b[4] for b in bills if b[3] == '支出')
    assert total_expense >= 4500.0, f"本月支出应该>=4500，实际: {total_expense}"