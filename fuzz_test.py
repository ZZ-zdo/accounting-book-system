#!/usr/bin/env python3
"""
模糊测试脚本 - 针对 main18.py 的关键功能
使用 Atheris 进行模糊测试
"""

import atheris
import sys
import os
import sqlite3
import traceback
from io import StringIO
from contextlib import redirect_stderr, redirect_stdout

# 导入被测试的模块
with atheris.instrument_imports():
    from main18 import Database


# ============================================
# 模糊测试1:  用户注册功能
# ============================================

@atheris.instrument_func
def fuzz_register_user(data):
    """
    模糊测试用户注册功能
    
    测试目标: 
    - 各种异常用户名
    - 各种异常密码
    - 各种异常手机号
    - SQL 注入尝试
    """
    if len(data) < 3:
        return
    
    # 清理测试数据库
    test_db = "fuzz_test_register. db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    try:
        db = Database(db_name=test_db)
        
        # 分割输入数据为三部分
        fdp = atheris.FuzzedDataProvider(data)
        
        # 生成模糊数据
        username = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1000))
        password = fdp.ConsumeUnicodeNoSurrogates(fdp. ConsumeIntInRange(0, 1000))
        phone = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
        
        # 抑制输出
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            # 执行注册
            result = db.register_user(username, password, phone)
        
        # 不期望任何崩溃
        # 如果到这里没有异常，说明函数处理了输入
        
    except sqlite3.Error as e:
        # SQLite 错误是可以接受的
        pass
    except UnicodeDecodeError:
        # 编码错误是可以接受的
        pass
    except Exception as e:
        # 记录崩溃
        crash_type = type(e).__name__
        print(f"\n🔥 CRASH FOUND in register_user!")
        print(f"Exception:  {crash_type}:  {str(e)}")
        print(f"Username: {repr(username)}")
        print(f"Password: {repr(password)}")
        print(f"Phone: {repr(phone)}")
        print(f"Traceback:\n{traceback.format_exc()}")
        
        # 保存崩溃输入
        crash_file = f"crash_register_{crash_type}. bin"
        with open(crash_file, "wb") as f:
            f.write(data)
        print(f"Crash input saved to: {crash_file}")
        
        # 不 raise，继续模糊测试
    finally:
        # 清理
        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except: 
                pass


# ============================================
# 模糊测试2: 账单添加功能
# ============================================

@atheris.instrument_func
def fuzz_add_bill(data):
    """
    模糊测试账单添加功能
    
    测试目标:
    - 各种异常金额 (负数、超大数、NaN、Inf)
    - 各种异常日期格式
    - SQL 注入尝试
    - 类型混淆攻击
    """
    if len(data) < 10:
        return
    
    test_db = "fuzz_test_bill.db"
    if os. path.exists(test_db):
        os.remove(test_db)
    
    try:
        db = Database(db_name=test_db)
        
        # 创建测试用户和账户
        success, user_id = db.register_user("fuzzuser", "fuzzpass")
        if not success:
            return
        
        account_id = db.create_account(user_id, "fuzzaccount", 10000.0)
        
        # 生成模糊数据
        fdp = atheris.FuzzedDataProvider(data)
        
        # 模糊的账单类型
        bill_type_choice = fdp.ConsumeIntInRange(0, 4)
        bill_types = ["支出", "收入", "", "INVALID", fdp.ConsumeUnicodeNoSurrogates(10)]
        bill_type = bill_types[bill_type_choice]
        
        # 模糊的金额 (尝试各种边界情况)
        amount_choice = fdp.ConsumeIntInRange(0, 10)
        if amount_choice == 0:
            amount = fdp.ConsumeFloat()  # 随机浮点数
        elif amount_choice == 1:
            amount = -fdp.ConsumeFloat()  # 负数
        elif amount_choice == 2:
            amount = float('inf')  # 无穷大
        elif amount_choice == 3:
            amount = float('-inf')  # 负无穷
        elif amount_choice == 4:
            amount = float('nan')  # NaN
        elif amount_choice == 5:
            amount = 0.0  # 零
        elif amount_choice == 6:
            amount = 1e308  # 极大数
        elif amount_choice == 7:
            amount = 1e-308  # 极小数
        elif amount_choice == 8:
            # 尝试类型混淆
            amount = fdp.ConsumeUnicodeNoSurrogates(20)
        else:
            amount = fdp.ConsumeIntInRange(-1000000, 1000000)
        
        # 模糊的日期
        date_choice = fdp. ConsumeIntInRange(0, 5)
        if date_choice == 0:
            bill_date = fdp.ConsumeUnicodeNoSurrogates(50)  # 随机字符串
        elif date_choice == 1:
            bill_date = "9999-99-99"  # 无效日期
        elif date_choice == 2:
            bill_date = "0000-00-00"
        elif date_choice == 3:
            bill_date = "'; DROP TABLE bills; --"  # SQL 注入
        elif date_choice == 4:
            bill_date = "\x00\x00\x00"  # 空字节
        else:
            bill_date = "2025-12-12"  # 正常日期
        
        # 模糊的备注
        remark = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 10000))
        
        # 尝试添加账单
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            result = db.add_bill(
                user_id=user_id,
                account_id=account_id,
                bill_type=bill_type,
                amount=amount,
                bill_date=bill_date,
                tag_id=None,
                remark=remark
            )
        
    except sqlite3.Error as e:
        # SQLite 错误是可接受的
        pass
    except (ValueError, TypeError) as e:
        # 类型转换错误是可接受的
        pass
    except Exception as e:
        # 记录崩溃
        crash_type = type(e).__name__
        print(f"\n🔥 CRASH FOUND in add_bill!")
        print(f"Exception: {crash_type}: {str(e)}")
        print(f"Bill type:  {repr(bill_type)}")
        print(f"Amount: {repr(amount)}")
        print(f"Date: {repr(bill_date)}")
        print(f"Remark length: {len(remark) if isinstance(remark, str) else 'N/A'}")
        print(f"Traceback:\n{traceback.format_exc()}")
        
        # 保存崩溃输入
        crash_file = f"crash_add_bill_{crash_type}.bin"
        with open(crash_file, "wb") as f:
            f.write(data)
        print(f"Crash input saved to: {crash_file}")
        
    finally:
        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except:
                pass


# ============================================
# 模糊测试3: 查询功能
# ============================================

@atheris.instrument_func
def fuzz_get_bills(data):
    """
    模糊测试账单查询功能
    
    测试目标:
    - SQL 注入
    - 异常参数组合
    - 边界条件
    """
    if len(data) < 5:
        return
    
    test_db = "fuzz_test_query.db"
    if os. path.exists(test_db):
        os.remove(test_db)
    
    try:
        db = Database(db_name=test_db)
        
        # 创建测试数据
        success, user_id = db.register_user("queryuser", "pass")
        if not success:
            return
        
        account_id = db.create_account(user_id, "account", 1000.0)
        
        # 生成模糊查询参数
        fdp = atheris.FuzzedDataProvider(data)
        
        # 模糊的日期范围
        start_date = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
        end_date = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
        
        # 模糊的账单类型
        bill_type = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))
        
        # 模糊的 ID (可能是负数、超大数)
        account_id_fuzz = fdp.ConsumeIntInRange(-1000000, 1000000)
        tag_id_fuzz = fdp.ConsumeIntInRange(-1000000, 1000000)
        
        # 执行查询
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            result = db.get_bills(
                user_id=user_id,
                account_id=account_id_fuzz if fdp.ConsumeBool() else None,
                tag_id=tag_id_fuzz if fdp.ConsumeBool() else None,
                start_date=start_date if fdp.ConsumeBool() else None,
                end_date=end_date if fdp. ConsumeBool() else None,
                bill_type=bill_type if fdp.ConsumeBool() else None
            )
        
    except sqlite3.Error:
        pass
    except Exception as e: 
        crash_type = type(e).__name__
        print(f"\n🔥 CRASH FOUND in get_bills!")
        print(f"Exception: {crash_type}: {str(e)}")
        print(f"Start date: {repr(start_date)}")
        print(f"End date: {repr(end_date)}")
        print(f"Bill type: {repr(bill_type)}")
        print(f"Traceback:\n{traceback. format_exc()}")
        
        crash_file = f"crash_get_bills_{crash_type}.bin"
        with open(crash_file, "wb") as f:
            f.write(data)
        print(f"Crash input saved to: {crash_file}")
        
    finally: 
        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except:
                pass


# ============================================
# 模糊测试4: 密码哈希功能
# ============================================

@atheris.instrument_func
def fuzz_hash_password(data):
    """
    模糊测试密码哈希功能
    
    测试目标:
    - 编码问题
    - 超长输入
    - 特殊字符
    """
    if len(data) < 1:
        return
    
    try:
        db = Database(db_name=": memory:")  # 使用内存数据库
        
        fdp = atheris.FuzzedDataProvider(data)
        password = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100000))
        
        # 执行哈希
        hash_result = db.hash_password(password)
        
        # 验证结果
        assert isinstance(hash_result, str), "Hash should return string"
        assert len(hash_result) > 0, "Hash should not be empty"
        
    except UnicodeDecodeError:
        pass  # 编码错误是可接受的
    except Exception as e:
        crash_type = type(e).__name__
        print(f"\n🔥 CRASH FOUND in hash_password!")
        print(f"Exception: {crash_type}:  {str(e)}")
        print(f"Password length: {len(data)}")
        print(f"Traceback:\n{traceback.format_exc()}")
        
        crash_file = f"crash_hash_{crash_type}.bin"
        with open(crash_file, "wb") as f:
            f.write(data)
        print(f"Crash input saved to: {crash_file}")


# ============================================
# 模糊测试5: 综合测试 (随机选择函数)
# ============================================

@atheris.instrument_func
def fuzz_comprehensive(data):
    """
    综合模糊测试 - 随机调用不同的函数
    """
    if len(data) < 2:
        return
    
    fdp = atheris.FuzzedDataProvider(data)
    
    # 随机选择一个测试目标
    choice = fdp.ConsumeIntInRange(0, 3)
    
    remaining_data = fdp.ConsumeBytes(fdp.remaining_bytes())
    
    if choice == 0:
        fuzz_register_user(remaining_data)
    elif choice == 1:
        fuzz_add_bill(remaining_data)
    elif choice == 2:
        fuzz_get_bills(remaining_data)
    else:
        fuzz_hash_password(remaining_data)


# ============================================
# 主函数
# ============================================

def main():
    """主函数 - 启动模糊测试"""
    
    # 创建崩溃输出目录
    os.makedirs("crashes", exist_ok=True)
    os.chdir("crashes")
    
    print("=" * 60)
    print("🔬 Starting Fuzzing Test for main18.py")
    print("=" * 60)
    print("Target functions:")
    print("  1. register_user()")
    print("  2. add_bill()")
    print("  3. get_bills()")
    print("  4. hash_password()")
    print("  5. Comprehensive (random)")
    print("=" * 60)
    print("Running...  (Press Ctrl+C to stop)")
    print("=" * 60)
    print()
    
    # 选择要运行的测试
    if len(sys.argv) > 1:
        test_choice = sys.argv[1]
        if test_choice == "register":
            atheris.Setup(sys.argv, fuzz_register_user)
        elif test_choice == "bill":
            atheris.Setup(sys.argv, fuzz_add_bill)
        elif test_choice == "query":
            atheris.Setup(sys.argv, fuzz_get_bills)
        elif test_choice == "hash":
            atheris.Setup(sys.argv, fuzz_hash_password)
        else:
            atheris.Setup(sys.argv, fuzz_comprehensive)
    else:
        # 默认运行综合测试
        atheris. Setup(sys.argv, fuzz_comprehensive)
    
    atheris.Fuzz()


if __name__ == "__main__": 
    main()

#python3 fuzz_test.py