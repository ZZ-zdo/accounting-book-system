#!/usr/bin/env python3
"""
手动崩溃测试 - 针对已知弱点
"""

from main18 import Database
import os

def test_crash_scenarios():
    """手动测试已知的崩溃场景"""
    
    print("🔬 Manual Crash Testing\n")
    
    test_db = "manual_test.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    db = Database(db_name=test_db)
    success, user_id = db.register_user("testuser", "testpass")
    account_id = db.create_account(user_id, "test", 1000.0)
    
    crash_count = 0
    
    # ========== 测试场景 ==========
    
    scenarios = [
        {
            "name": "无穷大金额",
            "params": (user_id, account_id, "支出", float('inf'), "2025-12-12", None, "test"),
        },
        {
            "name": "NaN金额",
            "params": (user_id, account_id, "支出", float('nan'), "2025-12-12", None, "test"),
        },
        {
            "name": "负无穷金额",
            "params": (user_id, account_id, "支出", float('-inf'), "2025-12-12", None, "test"),
        },
        {
            "name":  "字符串金额",
            "params": (user_id, account_id, "支出", "NOT_A_NUMBER", "2025-12-12", None, "test"),
        },
        {
            "name": "None金额",
            "params":  (user_id, account_id, "支出", None, "2025-12-12", None, "test"),
        },
        {
            "name": "超长备注",
            "params": (user_id, account_id, "支出", 100.0, "2025-12-12", None, "A" * 1000000),
        },
        {
            "name": "SQL注入日期",
            "params": (user_id, account_id, "支出", 100.0, "'; DROP TABLE bills; --", None, "test"),
        },
        {
            "name": "无效日期格式",
            "params": (user_id, account_id, "支出", 100.0, "9999-99-99", None, "test"),
        },
        {
            "name": "空字节",
            "params": (user_id, account_id, "支出", 100.0, "\x00\x00\x00", None, "test"),
        },
        {
            "name":  "超大数字",
            "params": (user_id, account_id, "支出", 1e308, "2025-12-12", None, "test"),
        },
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"[{i}/{len(scenarios)}] Testing: {scenario['name']}")
        try:
            result = db.add_bill(*scenario['params'])
            print(f"    ✅ Handled gracefully:  {result}")
        except Exception as e:
            crash_count += 1
            print(f"    🔥 CRASH! {type(e).__name__}: {str(e)[:100]}")
            
            # 保存崩溃信息
            crash_file = f"manual_crash_{scenario['name']. replace(' ', '_')}.txt"
            with open(crash_file, "w") as f:
                f.write(f"Scenario: {scenario['name']}\n")
                f.write(f"Exception: {type(e).__name__}\n")
                f.write(f"Message: {str(e)}\n")
                f.write(f"Params: {scenario['params']}\n")
            print(f"    Saved to: {crash_file}")
    
    print(f"\n{'='*60}")
    print(f"📊 Results:")
    print(f"   Total scenarios: {len(scenarios)}")
    print(f"   Crashes:  {crash_count}")
    print(f"   Pass rate: {(len(scenarios) - crash_count) / len(scenarios) * 100:.1f}%")
    print(f"{'='*60}")
    
    # 清理
    if os.path.exists(test_db):
        os.remove(test_db)


if __name__ == "__main__": 
    test_crash_scenarios()