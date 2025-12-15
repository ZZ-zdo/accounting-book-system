#!/usr/bin/env python3
"""
调试版模糊测试 - 显示详细运行信息
"""

import atheris
import sys
import os
import sqlite3
import traceback
from io import StringIO
from contextlib import redirect_stderr, redirect_stdout

with atheris.instrument_imports():
    from main18 import Database


# 全局计数器
test_counter = 0
crash_counter = 0


@atheris.instrument_func
def fuzz_add_bill_aggressive(data):
    """
    激进的账单测试 - 故意触发边界情况
    """
    global test_counter, crash_counter
    test_counter += 1
    
    if len(data) < 10:
        return
    
    # 每1000次测试输出一次进度
    if test_counter % 1000 == 0:
        print(f"\r[Progress] Tests: {test_counter}, Crashes: {crash_counter}", end="", flush=True)
    
    test_db = f"fuzz_test_{os.getpid()}.db"
    
    try:
        db = Database(db_name=test_db)
        
        # 创建基础数据
        success, user_id = db.register_user("fuzzuser", "fuzzpass")
        if not success:
            return
        
        account_id = db.create_account(user_id, "fuzzaccount", 10000.0)
        
        fdp = atheris.FuzzedDataProvider(data)
        
        # ========== 激进的测试用例 ==========
        
        # 1. 极端金额测试
        amount_tests = [
            float('inf'),           # 无穷大
            float('-inf'),          # 负无穷
            float('nan'),           # NaN
            1e308,                  # 接近浮点数上限
            -1e308,                 # 接近浮点数下限
            0.0,                    # 零
            -0.0,                   # 负零
            1e-308,                 # 极小正数
            -999999999999999,       # 超大负数
            "NOT_A_NUMBER",         # 字符串
            None,                   # None
            [],                     # 列表
            {},                     # 字典
            True,                   # 布尔值
        ]
        
        amount_choice = fdp.ConsumeIntInRange(0, len(amount_tests) - 1)
        amount = amount_tests[amount_choice]
        
        # 2. 极端日期测试
        date_tests = [
            "9999-99-99",                    # 无效日期
            "0000-00-00",                    # 零日期
            "'; DROP TABLE bills; --",       # SQL注入
            "1900-01-01",                    # 极早日期
            "2999-12-31",                    # 极晚日期
            "2025-02-30",                    # 不存在的日期
            "INVALID",                       # 完全无效
            "\x00\x00\x00",                 # 空字节
            "2025-12-12' OR '1'='1",        # SQL注入变体
            "<script>alert(1)</script>",    # XSS尝试
            "../../../etc/passwd",          # 路径遍历
            "A" * 10000,                    # 超长字符串
        ]
        
        date_choice = fdp.ConsumeIntInRange(0, len(date_tests) - 1)
        bill_date = date_tests[date_choice]
        
        # 3. 极端账单类型测试
        type_tests = [
            "支出",
            "收入",
            "",                             # 空字符串
            None,                           # None
            "INVALID_TYPE",                 # 无效类型
            "支出'; DROP TABLE accounts;--", # SQL注入
            "A" * 1000,                     # 超长字符串
            "\n\r\t",                       # 特殊字符
        ]
        
        type_choice = fdp.ConsumeIntInRange(0, len(type_tests) - 1)
        bill_type = type_tests[type_choice]
        
        # 4. 极端备注测试
        remark_tests = [
            "A" * 100000,                   # 10万字符
            "\x00" * 1000,                  # 空字节
            "🔥" * 10000,                   # 大量emoji
            "'; DELETE FROM bills; --",     # SQL注入
            "<script>alert(1)</script>",    # XSS
        ]
        
        if fdp.ConsumeBool():
            remark = remark_tests[fdp.ConsumeIntInRange(0, len(remark_tests) - 1)]
        else:
            remark = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50000))
        
        # 5. 执行测试
        # 不抑制输出，看看会发生什么
        result = db.add_bill(
            user_id=user_id,
            account_id=account_id,
            bill_type=bill_type,
            amount=amount,
            bill_date=bill_date,
            tag_id=None,
            remark=remark
        )
        
    except KeyboardInterrupt:
        raise
    except sqlite3.Error as e:
        # SQLite错误 - 记录但不算崩溃
        pass
    except (ValueError, TypeError) as e:
        # 预期的类型错误 - 记录但不算崩溃
        pass
    except MemoryError:
        # 内存错误 - 这是真正的崩溃
        crash_counter += 1
        print(f"\n\n🔥 MEMORY ERROR CRASH!")
        print(f"Amount: {repr(amount)}")
        print(f"Date: {repr(bill_date)}")
        print(f"Type: {repr(bill_type)}")
        print(f"Remark length: {len(remark) if isinstance(remark, str) else 'N/A'}")
        
        crash_file = f"crash_memory_{crash_counter}.bin"
        with open(crash_file, "wb") as f:
            f.write(data)
        print(f"Saved to: {crash_file}\n")
        
    except Exception as e:
        # 未预期的异常 - 这是崩溃
        crash_counter += 1
        crash_type = type(e).__name__
        
        print(f"\n\n🔥 CRASH #{crash_counter} FOUND!")
        print(f"Exception: {crash_type}:  {str(e)}")
        print(f"Amount: {repr(amount)}")
        print(f"Date: {repr(bill_date)}")
        print(f"Type: {repr(bill_type)}")
        print(f"Remark length: {len(remark) if isinstance(remark, str) else 'N/A'}")
        print(f"Traceback:")
        traceback.print_exc()
        
        crash_file = f"crash_{crash_type}_{crash_counter}.bin"
        with open(crash_file, "wb") as f:
            f.write(data)
        print(f"Saved to: {crash_file}\n")
        
    finally:
        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except: 
                pass


@atheris.instrument_func
def fuzz_sql_injection(data):
    """
    专门测试SQL注入
    """
    global test_counter, crash_counter
    test_counter += 1
    
    if len(data) < 5:
        return
    
    test_db = f"fuzz_sql_{os.getpid()}.db"
    
    try: 
        db = Database(db_name=test_db)
        success, user_id = db.register_user("sqluser", "sqlpass")
        if not success:
            return
        
        account_id = db.create_account(user_id, "account", 1000.0)
        db.add_bill(user_id, account_id, "支出", 100.0, "2025-12-12", None, "test")
        
        fdp = atheris.FuzzedDataProvider(data)
        
        # SQL注入payload
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE bills; --",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "' OR 1=1 --",
            "'; DELETE FROM accounts; --",
            "1' AND '1'='1",
            "' OR 'a'='a",
        ]
        
        # 测试查询函数
        payload_idx = fdp.ConsumeIntInRange(0, len(sql_payloads) - 1)
        payload = sql_payloads[payload_idx]
        
        # 尝试在不同参数中注入
        test_cases = [
            {"start_date": payload},
            {"end_date": payload},
            {"bill_type": payload},
        ]
        
        for params in test_cases:
            result = db.get_bills(user_id, **params)
            
            # 检查是否真的执行了注入
            # 如果表被删除了，下次查询会失败
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            conn.close()
            
            required_tables = ['users', 'accounts', 'bills', 'tags']
            for table_name in required_tables:
                if not any(table_name in t[0] for t in tables):
                    crash_counter += 1
                    print(f"\n\n🔥 SQL INJECTION SUCCESS!")
                    print(f"Table '{table_name}' was dropped!")
                    print(f"Payload: {payload}")
                    
                    crash_file = f"crash_sql_injection_{crash_counter}.bin"
                    with open(crash_file, "wb") as f:
                        f.write(data)
                    print(f"Saved to: {crash_file}\n")
                    return
        
    except sqlite3.Error as e:
        # 检查是否是因为注入导致的错误
        if "no such table" in str(e).lower():
            crash_counter += 1
            print(f"\n\n🔥 SQL INJECTION - Table dropped!")
            print(f"Error: {e}")
            
            crash_file = f"crash_sql_dropped_{crash_counter}.bin"
            with open(crash_file, "wb") as f:
                f.write(data)
            print(f"Saved to:  {crash_file}\n")
    except Exception as e:
        pass
    finally:
        if os. path.exists(test_db):
            try:
                os. remove(test_db)
            except:
                pass


@atheris.instrument_func
def fuzz_race_condition(data):
    """
    测试并发/竞态条件
    """
    global test_counter
    test_counter += 1
    
    if len(data) < 3:
        return
    
    test_db = "fuzz_race. db"
    
    try: 
        db = Database(db_name=test_db)
        success, user_id = db. register_user("raceuser", "racepass")
        if not success:
            return
        
        account_id = db.create_account(user_id, "account", 1000.0)
        
        # 快速连续添加大量账单
        for i in range(100):
            db.add_bill(user_id, account_id, "支出", 10.0, "2025-12-12")
        
        # 检查余额一致性
        accounts = db.get_user_accounts(user_id)
        balance = accounts[0][2]
        
        # 理论余额:  1000 - 100*10 = 0
        if abs(balance - 0.0) > 0.01:
            print(f"\n\n🔥 RACE CONDITION DETECTED!")
            print(f"Expected balance: 0.0")
            print(f"Actual balance:  {balance}")
            print(f"Difference: {balance}")
            
            crash_file = f"crash_race_condition. bin"
            with open(crash_file, "wb") as f:
                f.write(data)
            print(f"Saved to: {crash_file}\n")
        
    except Exception as e: 
        pass
    finally:
        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except:
                pass


def main():
    """主函数"""
    
    os.makedirs("crashes", exist_ok=True)
    os.chdir("crashes")
    
    print("=" * 70)
    print("🔬 Aggressive Fuzzing Test - Debug Mode")
    print("=" * 70)
    print("Testing strategies:")
    print("  1. Extreme values (inf, nan, huge numbers)")
    print("  2. SQL injection attempts")
    print("  3. Type confusion")
    print("  4. Memory exhaustion")
    print("  5. Race conditions")
    print("=" * 70)
    print()
    
    # 选择测试目标
    if len(sys.argv) > 1 and sys.argv[1] == "sql":
        print("🎯 Focus:  SQL Injection")
        atheris.Setup(sys.argv, fuzz_sql_injection)
    elif len(sys.argv) > 1 and sys.argv[1] == "race":
        print("🎯 Focus:  Race Conditions")
        atheris.Setup(sys.argv, fuzz_race_condition)
    else:
        print("🎯 Focus: General Fuzzing")
        atheris.Setup(sys.argv, fuzz_add_bill_aggressive)
    
    try:
        atheris. Fuzz()
    except KeyboardInterrupt:
        print(f"\n\n{'='*70}")
        print(f"📊 Final Statistics:")
        print(f"   Total tests: {test_counter}")
        print(f"   Crashes found: {crash_counter}")
        print(f"{'='*70}")


if __name__ == "__main__":
    main()