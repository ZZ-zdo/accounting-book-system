import pytest
import os
import sqlite3
from datetime import datetime, timedelta
from main18 import Database, RecurringBillScheduler


# ============================================
# 🔺 方法一：自顶向下集成测试（Top-Down）
# ============================================

class TestTopDownIntegration:
    """
    自顶向下集成测试：模拟用户从注册到使用的完整业务流程
    测试路径：用户注册 -> 登录 -> 账户管理 -> 账单操作
    """
    
    @pytest.fixture(scope="function")
    def clean_db(self):
        """每个测试使用独立的数据库"""
        test_db = "test_top_down. db"
        if os.path.exists(test_db):
            os.remove(test_db)
        
        db = Database(db_name=test_db)
        db.init_database()
        yield db
        
        if os.path.exists(test_db):
            os.remove(test_db)
    
    def test_integration_01_complete_user_journey(self, clean_db):
        """
        【集成测试1 - 自顶向下】完整的用户使用旅程
        
        测试场景：
        新用户注册 -> 登录验证 -> 创建账户 -> 添加标签 -> 记账 -> 查询账单 -> 查看统计
        
        集成的模块：
        - 用户管理模块 (register_user, login_user)
        - 账户管理模块 (create_account, get_user_accounts)
        - 标签管理模块 (create_tag, get_user_tags)
        - 账单管理模块 (add_bill, get_bills)
        - 统计分析模块 (get_bill_statistics)
        """
        db = clean_db
        
        # ========== 阶段1：用户注册与登录 ==========
        print("\n【阶段1】用户注册与登录")
        
        # 1.1 注册新用户
        success, user_id = db.register_user("zhangsan", "password123", "13800138000")
        assert success is True, "用户注册应该成功"
        assert user_id is not None, "应该返回用户ID"
        print(f"✅ 用户注册成功，user_id={user_id}")
        
        # 1.2 验证默认标签是否创建
        default_tags = db.get_user_tags(user_id)
        assert len(default_tags) == 10, f"应该自动创建10个默认标签，实际:  {len(default_tags)}"
        print(f"✅ 默认标签创建成功，共 {len(default_tags)} 个")
        
        # 1.3 登录验证
        login_result = db.login_user("zhangsan", "password123")
        assert login_result is not None, "登录应该成功"
        assert login_result[0] == user_id, "登录返回的user_id应该匹配"
        assert login_result[1] == "zhangsan", "用户名应该匹配"
        print(f"✅ 登录成功，用户:  {login_result[1]}")
        
        # 1.4 错误密码应该失败
        failed_login = db.login_user("zhangsan", "wrongpassword")
        assert failed_login is None, "错误密码应该登录失败"
        print("✅ 错误密码登录被正确拒绝")
        
        # ========== 阶段2：账户管理 ==========
        print("\n【阶段2】账户管理")
        
        # 2.1 创建主账户
        main_account_id = db.create_account(user_id, "工资卡", 5000.0, 3000.0)
        assert main_account_id is not None, "创建账户应该成功"
        print(f"✅ 创建账户成功，account_id={main_account_id}")
        
        # 2.2 创建第二个账户
        saving_account_id = db.create_account(user_id, "储蓄卡", 10000.0, None)
        assert saving_account_id is not None, "创建第二个账户应该成功"
        print(f"✅ 创建储蓄账户成功，account_id={saving_account_id}")
        
        # 2.3 验证账户列表
        accounts = db.get_user_accounts(user_id)
        assert len(accounts) == 2, f"应该有2个账户，实际:  {len(accounts)}"
        assert accounts[0][1] == "工资卡", "第一个账户名称应该是'工资卡'"
        assert accounts[0][2] == 5000.0, "工资卡余额应该是5000"
        assert accounts[0][3] == 3000.0, "工资卡预算应该是3000"
        print(f"✅ 账户列表验证成功:  {[acc[1] for acc in accounts]}")
        
        # ========== 阶段3：标签管理 ==========
        print("\n【阶段3】标签管理")
        
        # 3.1 创建自定义标签
        success, custom_tag_id = db.create_tag(user_id, "零食", "支出", "#ff6b6b")
        assert success is True, "创建自定义标签应该成功"
        print(f"✅ 创建自定义标签成功，tag_id={custom_tag_id}")
        
        # 3.2 获取支出类标签
        expense_tags = db.get_user_tags(user_id, "支出")
        assert len(expense_tags) >= 8, f"支出标签应该>=8个，实际: {len(expense_tags)}"
        
        # 找到"餐饮"标签
        food_tag = next((t for t in expense_tags if t[1] == "餐饮"), None)
        assert food_tag is not None, "应该有'餐饮'标签"
        food_tag_id = food_tag[0]
        print(f"✅ 找到餐饮标签，tag_id={food_tag_id}")
        
        # ========== 阶段4：账单操作 ==========
        print("\n【阶段4】账单操作")
        
        # 4.1 添加收入账单（工资）
        salary_tags = db.get_user_tags(user_id, "收入")
        salary_tag = next((t for t in salary_tags if t[1] == "工资"), None)
        salary_tag_id = salary_tag[0] if salary_tag else None
        
        success, income_bill_id = db.add_bill(
            user_id=user_id,
            account_id=main_account_id,
            bill_type="收入",
            amount=8000.0,
            bill_date="2025-12-01",
            tag_id=salary_tag_id,
            remark="12月工资"
        )
        assert success is True, "添加收入账单应该成功"
        print(f"✅ 添加工资收入:  ¥8000")
        
        # 4.2 验证余额增加
        accounts = db.get_user_accounts(user_id)
        main_account = next(a for a in accounts if a[0] == main_account_id)
        assert main_account[2] == 13000.0, f"工资卡余额应该是13000(5000+8000)，实际: {main_account[2]}"
        print(f"✅ 余额更新正确:  ¥{main_account[2]}")
        
        # 4.3 添加多笔支出账单
        expenses = [
            (50.0, "2025-12-02", food_tag_id, "早餐"),
            (120.0, "2025-12-02", food_tag_id, "午餐聚餐"),
            (35.0, "2025-12-03", food_tag_id, "晚餐外卖"),
            (200.0, "2025-12-05", custom_tag_id, "买零食"),
        ]
        
        for amount, date, tag_id, remark in expenses:
            success, bill_id = db.add_bill(
                user_id, main_account_id, "支出", amount, date, tag_id, remark
            )
            assert success is True, f"添加账单应该成功: {remark}"
            print(f"✅ 添加支出:  {remark} -¥{amount}")
        
        # 4.4 验证最终余额
        accounts = db.get_user_accounts(user_id)
        main_account = next(a for a in accounts if a[0] == main_account_id)
        expected_balance = 13000.0 - (50 + 120 + 35 + 200)  # 12595
        assert main_account[2] == expected_balance, \
            f"余额应该是{expected_balance}，实际: {main_account[2]}"
        print(f"✅ 最终余额正确: ¥{main_account[2]}")
        
        # ========== 阶段5：账单查询 ==========
        print("\n【阶段5】账单查询")
        
        # 5.1 查询所有账单
        all_bills = db.get_bills(user_id)
        assert len(all_bills) == 5, f"应该有5条账单，实际: {len(all_bills)}"
        print(f"✅ 查询所有账单:  {len(all_bills)} 条")
        
        # 5.2 按类型查询（只查支出）
        expense_bills = db.get_bills(user_id, bill_type="支出")
        assert len(expense_bills) == 4, f"支出账单应该有4条，实际: {len(expense_bills)}"
        print(f"✅ 查询支出账单: {len(expense_bills)} 条")
        
        # 5.3 按标签查询（餐饮类）
        food_bills = db.get_bills(user_id, tag_id=food_tag_id)
        assert len(food_bills) == 3, f"餐饮账单应该有3条，实际: {len(food_bills)}"
        print(f"✅ 查询餐饮账单: {len(food_bills)} 条")
        
        # 5.4 按日期范围查询
        bills_dec2 = db.get_bills(
            user_id, 
            start_date="2025-12-02", 
            end_date="2025-12-02"
        )
        assert len(bills_dec2) == 2, f"12月2日应该有2条账单，实际: {len(bills_dec2)}"
        print(f"✅ 按日期查询: {len(bills_dec2)} 条")
        
        # ========== 阶段6：统计分析 ==========
        print("\n【阶段6】统计分析")
        
        # 6.1 获取12月统计
        stats = db.get_bill_statistics(
            user_id, 
            start_date="2025-12-01", 
            end_date="2025-12-31"
        )
        
        assert stats['total_income'] == 8000.0, \
            f"总收入应该是8000，实际: {stats['total_income']}"
        assert stats['total_expense'] == 405.0, \
            f"总支出应该是405，实际: {stats['total_expense']}"
        assert stats['balance'] == 7595.0, \
            f"结余应该是7595，实际: {stats['balance']}"
        
        print(f"✅ 收入:  ¥{stats['total_income']}")
        print(f"✅ 支出:  ¥{stats['total_expense']}")
        print(f"✅ 结余:  ¥{stats['balance']}")
        
        # 6.2 验证支出分类统计
        expense_by_tag = stats['expense_by_tag']
        assert len(expense_by_tag) == 2, "应该有2个支出类别"
        
        # 找到餐饮类别
        food_expense = next((e for e in expense_by_tag if e[0] == "餐饮"), None)
        assert food_expense is not None, "应该有餐饮类别统计"
        assert food_expense[1] == 205.0, f"餐饮支出应该是205，实际: {food_expense[1]}"
        print(f"✅ 餐饮支出: ¥{food_expense[1]}")
        
        # 找到零食类别
        snack_expense = next((e for e in expense_by_tag if e[0] == "零食"), None)
        assert snack_expense is not None, "应该有零食类别统计"
        assert snack_expense[1] == 200.0, f"零食支出应该是200，实际: {snack_expense[1]}"
        print(f"✅ 零食支出: ¥{snack_expense[1]}")
        
        # ========== 测试总结 ==========
        print("\n" + "="*60)
        print("🎉 自顶向下集成测试完成！")
        print("="*60)
        print(f"✅ 用户管理: 注册、登录、默认标签")
        print(f"✅ 账户管理: 创建2个账户、余额跟踪")
        print(f"✅ 标签管理: 默认标签 + 自定义标签")
        print(f"✅ 账单管理: 1笔收入 + 4笔支出")
        print(f"✅ 查询功能: 全部/类型/标签/日期筛选")
        print(f"✅ 统计分析: 收支统计、分类汇总")
        print("="*60)
    
    def test_integration_02_account_transfer_scenario(self, clean_db):
        """
        【集成测试2 - 自顶向下】账户间转账场景
        
        测试场景：
        用户注册 -> 创建两个账户 -> 从账户A支出 -> 向账户B收入（模拟转账）
        
        验证：
        - 两个账户余额变化的一致性
        - 跨账户的账单记录
        """
        db = clean_db
        
        print("\n【场景】模拟账户转账")
        
        # 1. 创建用户
        success, user_id = db.register_user("lisi", "pass456")
        assert success is True
        print(f"✅ 用户创建成功")
        
        # 2. 创建两个账户
        account_a_id = db.create_account(user_id, "支付宝", 1000.0)
        account_b_id = db.create_account(user_id, "微信", 500.0)
        print(f"✅ 账户A (支付宝) 余额: ¥1000")
        print(f"✅ 账户B (微信) 余额: ¥500")
        
        # 3. 从账户A转出300
        success, bill_a = db.add_bill(
            user_id, account_a_id, "支出", 300.0, 
            "2025-12-12", None, "转账到微信"
        )
        assert success is True
        
        # 4. 向账户B转入300
        success, bill_b = db.add_bill(
            user_id, account_b_id, "收入", 300.0, 
            "2025-12-12", None, "从支付宝转入"
        )
        assert success is True
        
        # 5. 验证余额
        accounts = db.get_user_accounts(user_id)
        account_a = next(a for a in accounts if a[0] == account_a_id)
        account_b = next(a for a in accounts if a[0] == account_b_id)
        
        assert account_a[2] == 700.0, f"账户A应该是700，实际: {account_a[2]}"
        assert account_b[2] == 800.0, f"账户B应该是800，实际:  {account_b[2]}"
        
        # 6. 验证总资产不变
        total_balance = account_a[2] + account_b[2]
        assert total_balance == 1500.0, f"总资产应该是1500，实际: {total_balance}"
        
        print(f"✅ 账户A 余额: ¥{account_a[2]}")
        print(f"✅ 账户B 余额: ¥{account_b[2]}")
        print(f"✅ 总资产:  ¥{total_balance} (保持不变)")
        print("\n🎉 转账场景测试通过！")


# ============================================
# 🔻 方法二：自底向上集成测试（Bottom-Up）
# ============================================

class TestBottomUpIntegration:
    """
    自底向上集成测试：从数据库层开始，逐步集成业务逻辑
    测试路径：数据库 -> 业务逻辑 -> 复杂功能
    """
    
    @pytest.fixture(scope="function")
    def clean_db(self):
        """每个测试使用独立的数据库"""
        test_db = "test_bottom_up. db"
        if os.path.exists(test_db):
            os.remove(test_db)
        
        db = Database(db_name=test_db)
        db.init_database()
        yield db
        
        if os.path.exists(test_db):
            os.remove(test_db)
    
    def test_integration_03_bill_tag_relationship(self, clean_db):
        """
        【集成测试3 - 自底向上】账单-标签关系完整性
        
        测试路径：
        数据库层(表创建) -> 标签管理 -> 账单管理 -> 标签删除后的账单处理
        
        验证：
        - 标签与账单的外键关系
        - 删除标签时的级联处理
        - 数据一致性
        """
        db = clean_db
        
        print("\n【测试】账单-标签关系完整性")
        
        # ========== 层1：数据库基础层 ==========
        print("\n【层1】数据库基础层")
        
        # 1.1 验证表结构
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        required_tables = ['users', 'accounts', 'tags', 'bills']
        for table in required_tables:
            assert table in tables, f"表 {table} 应该存在"
        print(f"✅ 数据库表结构完整:  {required_tables}")
        
        # ========== 层2：用户与标签管理 ==========
        print("\n【层2】用户与标签管理")
        
        # 2.1 创建用户（触发默认标签创建）
        success, user_id = db.register_user("wangwu", "pass789")
        assert success is True
        
        # 2.2 验证默认标签
        default_tags = db.get_user_tags(user_id)
        assert len(default_tags) == 10, "应该有10个默认标签"
        print(f"✅ 默认标签创建成功: {len(default_tags)} 个")
        
        # 2.3 创建自定义标签
        success, custom_tag_id = db.create_tag(user_id, "测试标签", "支出", "#ff0000")
        assert success is True
        print(f"✅ 自定义标签创建成功，ID={custom_tag_id}")
        
        # ========== 层3：账户与账单管理 ==========
        print("\n【层3】账户与账单管理")
        
        # 3.1 创建账户
        account_id = db.create_account(user_id, "测试账户", 1000.0)
        assert account_id is not None
        
        # 3.2 使用自定义标签添加账单
        success, bill_id_1 = db.add_bill(
            user_id, account_id, "支出", 100.0, 
            "2025-12-10", custom_tag_id, "使用自定义标签"
        )
        assert success is True
        print(f"✅ 账单1 (带自定义标签) 添加成功")
        
        # 3.3 使用默认标签添加账单
        food_tag = next(t for t in default_tags if t[1] == "餐饮")
        success, bill_id_2 = db.add_bill(
            user_id, account_id, "支出", 50.0, 
            "2025-12-11", food_tag[0], "使用默认标签"
        )
        assert success is True
        print(f"✅ 账单2 (带默认标签) 添加成功")
        
        # 3.4 添加无标签账单
        success, bill_id_3 = db.add_bill(
            user_id, account_id, "支出", 30.0, 
            "2025-12-12", None, "无标签账单"
        )
        assert success is True
        print(f"✅ 账单3 (无标签) 添加成功")
        
        # ========== 层4：标签删除与数据一致性 ==========
        print("\n【层4】标签删除与数据一致性")
        
        # 4.1 验证删除前的状态
        bills_before = db.get_bills(user_id, tag_id=custom_tag_id)
        assert len(bills_before) == 1, "自定义标签应该有1条账单"
        print(f"✅ 删除前：自定义标签关联 {len(bills_before)} 条账单")
        
        # 4.2 删除自定义标签
        success, message = db.delete_tag(custom_tag_id)
        assert success is True, f"删除标签应该成功:  {message}"
        print(f"✅ 标签删除成功")
        
        # 4.3 验证标签已删除
        remaining_tags = db.get_user_tags(user_id)
        tag_ids = [t[0] for t in remaining_tags]
        assert custom_tag_id not in tag_ids, "自定义标签应该已删除"
        print(f"✅ 标签已从标签表删除")
        
        # 4.4 验证账单标签字段被置空（而非删除账单）
        all_bills = db.get_bills(user_id)
        assert len(all_bills) == 3, "账单总数应该还是3条"
        
        # 找到原来使用自定义标签的账单
        bill_1 = next(b for b in all_bills if b[0] == bill_id_1)
        assert bill_1[2] is None or bill_1[2] == "无标签", \
            f"账单1的标签应该被置空，实际: {bill_1[2]}"
        print(f"✅ 账单保留，标签字段已置空")
        
        # 4.5 验证其他账单不受影响
        bill_2 = next(b for b in all_bills if b[0] == bill_id_2)
        assert bill_2[2] == "餐饮", "账单2的标签应该不受影响"
        print(f"✅ 其他账单标签不受影响")
        
        # 4.6 验证数据一致性
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 验证没有孤儿标签（账单引用不存在的标签）
        cursor.execute("""
            SELECT COUNT(*) FROM bills 
            WHERE tag_id IS NOT NULL 
            AND tag_id NOT IN (SELECT tag_id FROM tags)
        """)
        orphan_count = cursor.fetchone()[0]
        assert orphan_count == 0, f"不应该有孤儿标签引用，实际: {orphan_count}"
        conn.close()
        print(f"✅ 数据一致性验证通过")
        
        print("\n🎉 账单-标签关系完整性测试通过！")
    
    def test_integration_04_recurring_bill_automation(self, clean_db):
        """
        【集成测试4 - 自底向上】固定账单自动化流程
        
        测试路径：
        数据库层 -> 固定账单规则 -> 调度器 -> 自动生成账单 -> 余额更新
        
        验证：
        - 固定账单规则的创建和存储
        - 调度器的执行逻辑
        - 自动生成账单的正确性
        - 余额的自动更新
        """
        db = clean_db
        
        print("\n【测试】固定账单自动化流程")
        
        # ========== 层1：基础数据准备 ==========
        print("\n【层1】基础数据准备")
        
        # 1.1 创建用户和账户
        success, user_id = db.register_user("zhaoliu", "pass000")
        account_id = db.create_account(user_id, "工资卡", 10000.0, 5000.0)
        
        # 1.2 获取标签
        tags = db.get_user_tags(user_id)
        rent_tag = next((t for t in tags if t[1] == "住房"), None)
        salary_tag = next((t for t in tags if t[1] == "工资"), None)
        
        print(f"✅ 用户和账户创建完成")
        
        # ========== 层2：创建固定账单规则 ==========
        print("\n【层2】创建固定账单规则")
        
        # 2.1 创建每月房租规则（每月10号）
        today = datetime.now().date()
        start_date = today.replace(day=1).strftime('%Y-%m-%d')  # 本月1号
        
        success, rent_rule_id = db.create_recurring_rule(
            user_id=user_id,
            account_id=account_id,
            bill_type="支出",
            amount=2000.0,
            frequency="每月",
            start_date=start_date,
            tag_id=rent_tag[0] if rent_tag else None,
            day_of_month=10,
            remark="房租"
        )
        assert success is True, "创建房租规则应该成功"
        print(f"✅ 房租规则创建成功 (每月10号, ¥2000)")
        
        # 2.2 创建每日打卡规则
        success, daily_rule_id = db.create_recurring_rule(
            user_id=user_id,
            account_id=account_id,
            bill_type="支出",
            amount=5.0,
            frequency="每日",
            start_date=start_date,
            tag_id=None,
            remark="每日打卡"
        )
        assert success is True, "创建每日规则应该成功"
        print(f"✅ 每日打卡规则创建成功 (¥5/天)")
        
        # 2.3 验证规则列表
        rules = db.get_recurring_rules(user_id, is_active=True)
        assert len(rules) == 2, f"应该有2条活动规则，实际: {len(rules)}"
        print(f"✅ 规则列表验证通过:  {len(rules)} 条")
        
        # ========== 层3：手动执行固定账单 ==========
        print("\n【层3】执行固定账单生成")
        
        # 3.1 记录执行前的余额
        accounts_before = db.get_user_accounts(user_id)
        balance_before = accounts_before[0][2]
        print(f"执行前余额: ¥{balance_before}")
        
        # 3.2 执行今天的固定账单
        executed_count = db.execute_recurring_bills(today)
        print(f"✅ 执行完成，生成了 {executed_count} 条账单")
        
        # 3.3 验证账单是否生成
        bills_today = db.get_bills(
            user_id,
            start_date=today.strftime('%Y-%m-%d'),
            end_date=today.strftime('%Y-%m-%d')
        )
        
        # 今天应该生成1条每日账单（如果今天不是10号，则只有每日）
        # 如果今天是10号，则应该有2条
        if today.day == 10:
            expected_bills = 2
            expected_deduction = 2005.0  # 2000房租 + 5打卡
        else:
            expected_bills = 1
            expected_deduction = 5.0  # 只有打卡
        
        assert len(bills_today) == expected_bills, \
            f"今天应该生成{expected_bills}条账单，实际: {len(bills_today)}"
        print(f"✅ 生成账单数量正确: {len(bills_today)} 条")
        
        # 3.4 验证账单备注包含"[自动]"
        for bill in bills_today:
            assert "[自动]" in bill[6], f"自动账单备注应该包含[自动]，实际: {bill[6]}"
        print(f"✅ 账单备注包含[自动]标记")
        
        # 3.5 验证余额扣减
        accounts_after = db. get_user_accounts(user_id)
        balance_after = accounts_after[0][2]
        actual_deduction = balance_before - balance_after
        
        assert actual_deduction == expected_deduction, \
            f"余额应该扣减{expected_deduction}，实际扣减:  {actual_deduction}"
        print(f"✅ 余额扣减正确: ¥{balance_before} -> ¥{balance_after}")
        
        # ========== 层4：验证幂等性（重复执行不会重复生成） ==========
        print("\n【层4】验证执行幂等性")
        
        # 4.1 再次执行今天的固定账单
        executed_count_2 = db.execute_recurring_bills(today)
        assert executed_count_2 == 0, f"重复执行应该返回0，实际: {executed_count_2}"
        print(f"✅ 重复执行不会重复生成账单")
        
        # 4.2 验证账单总数没有增加
        bills_today_2 = db.get_bills(
            user_id,
            start_date=today.strftime('%Y-%m-%d'),
            end_date=today.strftime('%Y-%m-%d')
        )
        assert len(bills_today_2) == expected_bills, \
            "账单数量不应该增加"
        print(f"✅ 账单数量保持不变: {len(bills_today_2)} 条")
        
        # ========== 层5：验证规则停用功能 ==========
        print("\n【层5】验证规则停用")
        
        # 5.1 停用每日规则
        db.toggle_recurring_rule(daily_rule_id, is_active=False)
        
        # 5.2 模拟明天执行
        tomorrow = today + timedelta(days=1)
        executed_count_tomorrow = db.execute_recurring_bills(tomorrow)
        
        # 明天应该只执行房租规则（如果明天是10号）或0条
        if tomorrow.day == 10:
            assert executed_count_tomorrow == 1, "只有房租规则应该执行"
        else:
            assert executed_count_tomorrow == 0, "没有规则应该执行"
        
        print(f"✅ 停用规则生效: 明天执行了 {executed_count_tomorrow} 条")
        
        # ========== 层6：集成调度器 ==========
        print("\n【层6】集成调度器（模拟）")
        
        # 6.1 创建调度器实例
        scheduler = RecurringBillScheduler(db)
        assert scheduler.db == db, "调度器应该持有数据库引用"
        assert scheduler.running is False, "调度器初始状态应该是停止"
        print(f"✅ 调度器创建成功")
        
        # 注意：实际的调度器测试需要 mock 或等待，这里只验证接口
        # scheduler.start()  # 不实际启动，避免后台线程
        # scheduler.stop()
        
        print("\n🎉 固定账单自动化流程测试通过！")


# ============================================
# 🔀 混合测试：跨模块边界测试
# ============================================

class TestCrossModuleBoundary:
    """
    跨模块边界测试：测试模块间的特殊交互场景
    """
    
    @pytest.fixture(scope="function")
    def clean_db(self):
        test_db = "test_cross_module. db"
        if os.path.exists(test_db):
            os.remove(test_db)
        
        db = Database(db_name=test_db)
        db.init_database()
        yield db
        
        if os.path.exists(test_db):
            os.remove(test_db)
    
    def test_integration_05_account_deletion_impact(self, clean_db):
        """
        【集成测试5 - 跨模块】账户删除对账单的影响
        
        测试场景：
        创建账户 -> 添加账单 -> 删除账户 -> 验证账单状态
        
        注意：你的代码没有实现 delete_account，
        这里展示如果有该功能应该如何测试
        """
        db = clean_db
        
        print("\n【测试】账户删除对账单的影响")
        
        # 创建用户和账户
        success, user_id = db.register_user("testuser", "pass")
        account_id = db. create_account(user_id, "临时账户", 1000.0)
        
        # 添加账单
        db.add_bill(user_id, account_id, "支出", 100.0, "2025-12-12")
        
        # 如果有删除账户功能，应该：
        # 1. 禁止删除有账单的账户
        # 2. 或者级联删除账单
        # 3. 或者将账单的 account_id 置空
        
        print("✅ 此测试展示了跨模块边界测试的思路")
        print("💡 建议：为 Database 类添加 delete_account 方法")


# ============================================
# 运行配置
# ============================================

if __name__ == "__main__": 
    pytest.main([__file__, "-v", "-s"])


#pytest test_integration.py -v -s