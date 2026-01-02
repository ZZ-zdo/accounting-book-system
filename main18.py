import sqlite3
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import calendar
import threading
import time

import sqlite3
import hashlib
import sys
import os

# ✅ 检测是否在测试环境
IS_TESTING = 'pytest' in sys.modules or 'PYTEST_CURRENT_TEST' in os. environ

# 只在非测试环境导入 tkinter
if not IS_TESTING:
    import tkinter as tk
    from tkinter import ttk, messagebox
else:
    # 测试环境下的 mock
    print("Running in test mode, skipping tkinter import")
    
    class MockMessageBox:
        @staticmethod
        def showwarning(*args, **kwargs):
            print(f"[MockWarning] {args}")
        
        @staticmethod
        def showinfo(*args, **kwargs):
            print(f"[MockInfo] {args}")
        
        @staticmethod
        def showerror(*args, **kwargs):
            print(f"[MockError] {args}")
        
        @staticmethod
        def askyesno(*args, **kwargs):
            print(f"[MockYesNo] {args}")
            return True
    
    messagebox = MockMessageBox()

from datetime import datetime, timedelta
import calendar
import threading
import time



class Database:
    """数据库管理类"""
    
    def __init__(self, db_name='accounting.db'):
        self.db_name = db_name
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name)
    
    def init_database(self):
        """初始化数据库表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 账户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                account_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                account_name TEXT NOT NULL,
                initial_balance REAL DEFAULT 0,
                current_balance REAL DEFAULT 0,
                monthly_budget REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # 标签表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tag_name TEXT NOT NULL,
                tag_type TEXT NOT NULL,
                color TEXT DEFAULT '#3498db',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE (user_id, tag_name)
            )
        ''')
        
        # 账单表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bills (
                bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                tag_id INTEGER,
                bill_type TEXT NOT NULL,
                amount REAL NOT NULL,
                bill_date DATE NOT NULL,
                remark TEXT,
                is_recurring BOOLEAN DEFAULT 0,
                recurring_rule_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (account_id) REFERENCES accounts(account_id),
                FOREIGN KEY (tag_id) REFERENCES tags(tag_id)
            )
        ''')
        
        # 固定账单规则表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recurring_rules (
                rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                tag_id INTEGER,
                bill_type TEXT NOT NULL,
                amount REAL NOT NULL,
                frequency TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE,
                day_of_month INTEGER,
                day_of_week INTEGER,
                remark TEXT,
                is_active BOOLEAN DEFAULT 1,
                last_executed_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (account_id) REFERENCES accounts(account_id),
                FOREIGN KEY (tag_id) REFERENCES tags(tag_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register_user(self, username, password, phone=''):
        if not username or not username.strip():
            return False, "用户名不能为空"
    
        username = username.strip()
        if len(username) < 3:
            return False, "用户名长度不能少于3个字符"
    
        if len(username) > 20:
            return False, "用户名长度不能超过20个字符"

        if not password or not password.strip():
            return False, "密码不能为空"
    
        if len(password) < 3:
            return False, "密码长度不能少于3个字符"
    
        if len(password) > 32:
            return False, "密码长度不能超过32个字符"

        if phone and phone.strip():
            phone = phone.strip()
            if not phone.isdigit():
                return False, "手机号只能包含数字"
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            password_hash = self.hash_password(password)
            cursor.execute(
                'INSERT INTO users (username, password_hash, phone) VALUES (?, ?, ?)',
                (username, password_hash, phone)
            )
            conn.commit()
            user_id = cursor.lastrowid
            self.create_default_tags(user_id, cursor)
            conn.commit()
            conn.close()
            return True, user_id
        except sqlite3.IntegrityError:
            return False, "用户名已存在"
    
    def create_default_tags(self, user_id, cursor):
        default_tags = [
            ('餐饮', '支出', '#e74c3c'),
            ('交通', '支出', '#3498db'),
            ('购物', '支出', '#9b59b6'),
            ('娱乐', '支出', '#f39c12'),
            ('医疗', '支出', '#1abc9c'),
            ('教育', '支出', '#34495e'),
            ('住房', '支出', '#e67e22'),
            ('工资', '收入', '#27ae60'),
            ('奖金', '收入', '#2ecc71'),
            ('投资', '收入', '#16a085'),
        ]
        for tag_name, tag_type, color in default_tags:
            try:
                cursor.execute(
                    'INSERT INTO tags (user_id, tag_name, tag_type, color) VALUES (?, ?, ?, ?)',
                    (user_id, tag_name, tag_type, color)
                )
            except sqlite3.IntegrityError:
                pass
    
    def login_user(self, username, password):
        conn = self.get_connection()
        cursor = conn.cursor()
        password_hash = self.hash_password(password)
        cursor.execute(
            'SELECT user_id, username FROM users WHERE username=? AND password_hash=?',
            (username, password_hash)
        )
        result = cursor.fetchone()
        conn.close()
        return result
    
    def update_user_info(self, user_id, phone=None, new_password=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        if phone:
            cursor.execute('UPDATE users SET phone=? WHERE user_id=?', (phone, user_id))
        if new_password:
            password_hash = self.hash_password(new_password)
            cursor.execute('UPDATE users SET password_hash=? WHERE user_id=?', (password_hash, user_id))
        conn.commit()
        conn.close()
        return True
    
    def create_account(self, user_id, account_name, initial_balance, monthly_budget=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO accounts (user_id, account_name, initial_balance, current_balance, monthly_budget)
               VALUES (?, ?, ?, ?, ?)''',
            (user_id, account_name, initial_balance, initial_balance, monthly_budget)
        )
        conn.commit()
        account_id = cursor.lastrowid
        conn.close()
        return account_id
    
    def get_user_accounts(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT account_id, account_name, current_balance, monthly_budget FROM accounts WHERE user_id=?',
            (user_id,)
        )
        accounts = cursor.fetchall()
        conn.close()
        return accounts
    
    def create_tag(self, user_id, tag_name, tag_type, color='#3498db'):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO tags (user_id, tag_name, tag_type, color) VALUES (?, ?, ?, ?)',
                (user_id, tag_name, tag_type, color)
            )
            conn.commit()
            tag_id = cursor.lastrowid
            conn.close()
            return True, tag_id
        except sqlite3.IntegrityError:
            return False, "标签名称已存在"
    
    def get_user_tags(self, user_id, tag_type=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        if tag_type:
            cursor.execute(
                'SELECT tag_id, tag_name, tag_type, color FROM tags WHERE user_id=? AND tag_type=? ORDER BY created_at',
                (user_id, tag_type)
            )
        else:
            cursor.execute(
                'SELECT tag_id, tag_name, tag_type, color FROM tags WHERE user_id=? ORDER BY tag_type, created_at',
                (user_id,)
            )
        tags = cursor.fetchall()
        conn.close()
        return tags
    
    def update_tag(self, tag_id, tag_name=None, color=None):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if tag_name and color:
                cursor.execute('UPDATE tags SET tag_name=?, color=? WHERE tag_id=?', (tag_name, color, tag_id))
            elif tag_name:
                cursor.execute('UPDATE tags SET tag_name=? WHERE tag_id=?', (tag_name, tag_id))
            elif color:
                cursor.execute('UPDATE tags SET color=? WHERE tag_id=?', (color, tag_id))
            conn.commit()
            conn.close()
            return True, "更新成功"
        except sqlite3.IntegrityError:
            return False, "标签名称已存在"
    
    def delete_tag(self, tag_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM bills WHERE tag_id=?', (tag_id,))
        count = cursor.fetchone()[0]
        if count > 0:
            cursor.execute('UPDATE bills SET tag_id=NULL WHERE tag_id=?', (tag_id,))
        cursor.execute('DELETE FROM tags WHERE tag_id=?', (tag_id,))
        conn.commit()
        conn.close()
        return True, "删除成功"
    
    def add_bill(self, user_id, account_id, bill_type, amount, bill_date, tag_id=None, remark='', 
                 is_recurring=False, recurring_rule_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''INSERT INTO bills (user_id, account_id, tag_id, bill_type, amount, bill_date, remark, 
                                     is_recurring, recurring_rule_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (user_id, account_id, tag_id, bill_type, amount, bill_date, remark, 
                 1 if is_recurring else 0, recurring_rule_id)
            )
            if bill_type == '支出':
                cursor.execute(
                    'UPDATE accounts SET current_balance = current_balance - ? WHERE account_id=?',
                    (amount, account_id)
                )
            else:
                cursor.execute(
                    'UPDATE accounts SET current_balance = current_balance + ? WHERE account_id=?',
                    (amount, account_id)
                )
            conn.commit()
            bill_id = cursor.lastrowid
            self.check_budget_warning(cursor, account_id)
            conn.close()
            return True, bill_id
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)
        
    def check_budget_warning(self, cursor, account_id):
        """检查预算预警"""
        cursor.execute(
            'SELECT monthly_budget, user_id FROM accounts WHERE account_id=?',
            (account_id,)
        )
        result = cursor.fetchone()
        if not result or not result[0]:
            return
        
        monthly_budget, user_id = result
        
        current_month = datetime.now().strftime('%Y-%m')
        cursor.execute(
            '''SELECT SUM(amount) FROM bills 
               WHERE account_id=? AND bill_type='支出' AND strftime('%Y-%m', bill_date)=?''',
            (account_id, current_month)
        )
        total_expense = cursor.fetchone()[0] or 0
        
        if total_expense >= monthly_budget * 0.9:
            usage_rate = (total_expense / monthly_budget) * 100
            messagebox.showwarning(
                "预算预警",
                f"本月预算已使用 {usage_rate:.1f}%\n本月支出: ¥{total_expense:.2f}\n预算: ¥{monthly_budget:.2f}"
            )
    
    def get_bills(self, user_id, account_id=None, tag_id=None, start_date=None, end_date=None, bill_type=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        query = '''SELECT b.bill_id, a.account_name, t.tag_name, b.bill_type, b.amount, b.bill_date, b.remark, 
                          b.is_recurring
                   FROM bills b 
                   JOIN accounts a ON b.account_id = a.account_id
                   LEFT JOIN tags t ON b.tag_id = t.tag_id
                   WHERE b.user_id=?'''
        params = [user_id]
        if account_id:
            query += ' AND b.account_id=?'
            params.append(account_id)
        if tag_id:
            query += ' AND b.tag_id=?'
            params.append(tag_id)
        if start_date:
            query += ' AND b.bill_date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND b.bill_date <= ?'
            params.append(end_date)
        if bill_type:
            query += ' AND b.bill_type=?'
            params.append(bill_type)
        query += ' ORDER BY b.bill_date DESC, b.created_at DESC'
        cursor.execute(query, params)
        bills = cursor.fetchall()
        conn.close()
        return bills
    
    def delete_bill(self, bill_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT account_id, bill_type, amount FROM bills WHERE bill_id=?', (bill_id,))
            result = cursor.fetchone()
            if not result:
                return False, "账单不存在"
            account_id, bill_type, amount = result
            cursor.execute('DELETE FROM bills WHERE bill_id=?', (bill_id,))
            if bill_type == '支出':
                cursor.execute(
                    'UPDATE accounts SET current_balance = current_balance + ? WHERE account_id=?',
                    (amount, account_id)
                )
            else:
                cursor.execute(
                    'UPDATE accounts SET current_balance = current_balance - ? WHERE account_id=?',
                    (amount, account_id)
                )
            conn.commit()
            conn.close()
            return True, "删除成功"
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)
    
    def get_bill_statistics(self, user_id, start_date=None, end_date=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        date_filter = ''
        params = [user_id]
        if start_date and end_date:
            date_filter = ' AND bill_date BETWEEN ? AND ?'
            params.extend([start_date, end_date])
        cursor.execute(
            f'''SELECT 
                    SUM(CASE WHEN bill_type='收入' THEN amount ELSE 0 END) as total_income,
                    SUM(CASE WHEN bill_type='支出' THEN amount ELSE 0 END) as total_expense
                FROM bills WHERE user_id=?{date_filter}''',
            params
        )
        result = cursor.fetchone()
        total_income = result[0] or 0
        total_expense = result[1] or 0
        cursor.execute(
            f'''SELECT t.tag_name, SUM(b.amount) as total
                FROM bills b
                LEFT JOIN tags t ON b.tag_id = t.tag_id
                WHERE b.user_id=? AND b.bill_type='支出'{date_filter}
                GROUP BY b.tag_id
                ORDER BY total DESC''',
            params
        )
        expense_by_tag = cursor.fetchall()
        cursor.execute(
            f'''SELECT t.tag_name, SUM(b.amount) as total
                FROM bills b
                LEFT JOIN tags t ON b.tag_id = t.tag_id
                WHERE b.user_id=? AND b.bill_type='收入'{date_filter}
                GROUP BY b.tag_id
                ORDER BY total DESC''',
            params
        )
        income_by_tag = cursor.fetchall()
        conn.close()
        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': total_income - total_expense,
            'expense_by_tag': expense_by_tag,
            'income_by_tag': income_by_tag
        }
    
    def create_recurring_rule(self, user_id, account_id, bill_type, amount, frequency, 
                            start_date, tag_id=None, end_date=None, day_of_month=None, 
                            day_of_week=None, remark=''):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO recurring_rules 
                   (user_id, account_id, tag_id, bill_type, amount, frequency, start_date, 
                    end_date, day_of_month, day_of_week, remark, is_active, last_executed_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, NULL)''',
                (user_id, account_id, tag_id, bill_type, amount, frequency, start_date,
                 end_date, day_of_month, day_of_week, remark)
            )
            conn.commit()
            rule_id = cursor.lastrowid
            conn.close()
            return True, rule_id
        except Exception as e:
            return False, str(e)
    
    def get_recurring_rules(self, user_id, is_active=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        query = '''SELECT r.rule_id, a.account_name, t.tag_name, r.bill_type, r.amount, 
                          r.frequency, r.start_date, r.end_date, r.remark, r.is_active, 
                          r.last_executed_date, r.day_of_month, r.day_of_week, r.account_id, r.tag_id
                   FROM recurring_rules r
                   JOIN accounts a ON r.account_id = a.account_id
                   LEFT JOIN tags t ON r.tag_id = t.tag_id
                   WHERE r.user_id=?'''
        params = [user_id]
        if is_active is not None:
            query += ' AND r.is_active=?'
            params.append(1 if is_active else 0)
        query += ' ORDER BY r.created_at DESC'
        cursor.execute(query, params)
        rules = cursor.fetchall()
        conn.close()
        return rules
    
    def toggle_recurring_rule(self, rule_id, is_active):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE recurring_rules SET is_active=? WHERE rule_id=?', 
                      (1 if is_active else 0, rule_id))
        conn.commit()
        conn.close()
        return True
    
    def delete_recurring_rule(self, rule_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM recurring_rules WHERE rule_id=?', (rule_id,))
        conn.commit()
        conn.close()
        return True, "删除成功"
    
    def execute_recurring_bills(self, today=None):
        if today is None:
            today = datetime.now().date()
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT rule_id, user_id, account_id, tag_id, bill_type, amount, frequency,
                   start_date, end_date, day_of_month, day_of_week, remark, last_executed_date
            FROM recurring_rules
            WHERE is_active=1
        ''')
        rules = cursor.fetchall()
        executed_count = 0
        for rule in rules:
            (rule_id, user_id, account_id, tag_id, bill_type, amount, frequency,
             start_date, end_date, day_of_month, day_of_week, remark, last_executed_date) = rule
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            if today < start_date_obj:
                continue
            if end_date:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                if today > end_date_obj:
                    continue
            if last_executed_date:
                last_exec = datetime.strptime(last_executed_date, '%Y-%m-%d').date()
                if last_exec == today:
                    continue
            should_execute = False
            if frequency == '每日':
                should_execute = True
            elif frequency == '每周':
                if day_of_week is not None and today.weekday() == day_of_week:
                    should_execute = True
            elif frequency == '每月':
                if day_of_month is not None and today.day == day_of_month:
                    should_execute = True
            elif frequency == '每年':
                if (start_date_obj.month == today.month and 
                    start_date_obj.day == today.day):
                    should_execute = True
            if should_execute:
                try:
                    cursor.execute(
                        '''INSERT INTO bills (user_id, account_id, tag_id, bill_type, amount, bill_date, 
                                             remark, is_recurring, recurring_rule_id)
                           VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)''',
                        (user_id, account_id, tag_id, bill_type, amount, today.strftime('%Y-%m-%d'),
                         f"[自动] {remark}", rule_id)
                    )
                    if bill_type == '支出':
                        cursor.execute(
                            'UPDATE accounts SET current_balance = current_balance - ? WHERE account_id=?',
                            (amount, account_id)
                        )
                    else:
                        cursor.execute(
                            'UPDATE accounts SET current_balance = current_balance + ? WHERE account_id=?',
                            (amount, account_id)
                        )
                    cursor.execute(
                        'UPDATE recurring_rules SET last_executed_date=? WHERE rule_id=?',
                        (today.strftime('%Y-%m-%d'), rule_id)
                    )
                    executed_count += 1
                except Exception as e:
                    print(f"执行固定账单规则 {rule_id} 失败: {e}")
                    continue
        conn.commit()
        conn.close()
        return executed_count


class RecurringBillScheduler:
    def __init__(self, db):
        self.db = db
        self.running = False
        self.thread = None
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            print("固定账单调度器已启动")
    
    def stop(self):
        self.running = False
        print("固定账单调度器已停止")
    
    def _run(self):
        last_check_date = None
        while self.running:
            today = datetime.now().date()
            if last_check_date != today:
                try:
                    count = self.db.execute_recurring_bills(today)
                    if count > 0:
                        print(f"自动生成了 {count} 条固定账单")
                    last_check_date = today
                except Exception as e:
                    print(f"执行固定账单时出错: {e}")
            time.sleep(3600)


class AccountingApp:
    def __init__(self):
        self.db = Database()
        self.current_user = None
        self.scheduler = RecurringBillScheduler(self.db)
        self.root = tk.Tk()
        self.root.title("记账本系统")
        self.root.geometry("1000x700")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.show_login_screen()
    
    def on_closing(self):
        self.scheduler.stop()
        self.root.destroy()
    
    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def show_login_screen(self):
        self.clear_window()
        self.scheduler.stop()
        frame = ttk.Frame(self.root, padding="50")
        frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        ttk.Label(frame, text="记账本系统", font=("Arial", 20, "bold")).grid(row=0, column=0, columnspan=2, pady=20)
        ttk.Label(frame, text="用户名:").grid(row=1, column=0, sticky=tk.W, pady=5)
        username_entry = ttk.Entry(frame, width=30)
        username_entry.grid(row=1, column=1, pady=5)
        ttk.Label(frame, text="密码:").grid(row=2, column=0, sticky=tk.W, pady=5)
        password_entry = ttk.Entry(frame, width=30, show="*")
        password_entry.grid(row=2, column=1, pady=5)
        
        def login():
            username = username_entry.get()
            password = password_entry.get()
            if not username or not password:
                messagebox.showerror("错误", "请输入用户名和密码")
                return
            result = self.db.login_user(username, password)
            if result:
                self.current_user = {'user_id': result[0], 'username': result[1]}
                self.scheduler.start()
                self.show_main_screen()
            else:
                messagebox.showerror("错误", "用户名或密码错误")
        
        ttk.Button(frame, text="登录", command=login).grid(row=3, column=0, columnspan=2, pady=20)
        ttk.Button(frame, text="注册", command=self.show_register_screen).grid(row=4, column=0, columnspan=2)
    
    def show_register_screen(self):
        self.clear_window()
        frame = ttk.Frame(self.root, padding="50")
        frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        ttk.Label(frame, text="用户注册", font=("Arial", 20, "bold")).grid(row=0, column=0, columnspan=2, pady=20)
        ttk.Label(frame, text="用户名:").grid(row=1, column=0, sticky=tk.W, pady=5)
        username_entry = ttk.Entry(frame, width=30)
        username_entry.grid(row=1, column=1, pady=5)
        ttk.Label(frame, text="密码:").grid(row=2, column=0, sticky=tk.W, pady=5)
        password_entry = ttk.Entry(frame, width=30, show="*")
        password_entry.grid(row=2, column=1, pady=5)
        ttk.Label(frame, text="确认密码:").grid(row=3, column=0, sticky=tk.W, pady=5)
        confirm_entry = ttk.Entry(frame, width=30, show="*")
        confirm_entry.grid(row=3, column=1, pady=5)
        ttk.Label(frame, text="手机号:").grid(row=4, column=0, sticky=tk.W, pady=5)
        phone_entry = ttk.Entry(frame, width=30)
        phone_entry.grid(row=4, column=1, pady=5)
        
        def register():
            username = username_entry.get()
            password = password_entry.get()
            confirm = confirm_entry.get()
            phone = phone_entry.get()
            if not username or not password:
                messagebox.showerror("错误", "用户名和密码不能为空")
                return
            if password != confirm:
                messagebox.showerror("错误", "两次密码输入不一致")
                return
            success, result = self.db.register_user(username, password, phone)
            if success:
                messagebox.showinfo("成功", "注册成功！已为您创建10个默认标签，请登录")
                self.show_login_screen()
            else:
                messagebox.showerror("错误", result)
        
        ttk.Button(frame, text="注册", command=register).grid(row=5, column=0, columnspan=2, pady=20)
        ttk.Button(frame, text="返回登录", command=self.show_login_screen).grid(row=6, column=0, columnspan=2)
    
    def show_main_screen(self):
        self.clear_window()
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(top_frame, text=f"欢迎, {self.current_user['username']}", font=("Arial", 12)).pack(side=tk.LEFT)
        ttk.Button(top_frame, text="个人信息", command=self.show_user_info).pack(side=tk.RIGHT, padx=5)
        ttk.Button(top_frame, text="退出登录", command=self.show_login_screen).pack(side=tk.RIGHT)
        
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        account_frame = ttk.Frame(notebook)
        notebook.add(account_frame, text="账户管理")
        self.setup_account_tab(account_frame)
        
        bill_frame = ttk.Frame(notebook)
        notebook.add(bill_frame, text="账单管理")
        self.setup_bill_tab(bill_frame)
        
        tag_frame = ttk.Frame(notebook)
        notebook.add(tag_frame, text="标签管理")
        self.setup_tag_tab(tag_frame)
        
        recurring_frame = ttk.Frame(notebook)
        notebook.add(recurring_frame, text="固定账单")
        self.setup_recurring_tab(recurring_frame)
        
        query_frame = ttk.Frame(notebook)
        notebook.add(query_frame, text="账单查询")
        self.setup_query_tab(query_frame)
        
        stats_frame = ttk.Frame(notebook)
        notebook.add(stats_frame, text="统计分析")
        self.setup_stats_tab(stats_frame)
    
    def setup_account_tab(self, parent):
        left_frame = ttk.LabelFrame(parent, text="创建新账户", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(left_frame, text="账户名称:").grid(row=0, column=0, sticky=tk.W, pady=5)
        account_name_entry = ttk.Entry(left_frame, width=25)
        account_name_entry.grid(row=0, column=1, pady=5)
        
        ttk.Label(left_frame, text="初始余额:").grid(row=1, column=0, sticky=tk.W, pady=5)
        balance_entry = ttk.Entry(left_frame, width=25)
        balance_entry.grid(row=1, column=1, pady=5)
        
        ttk.Label(left_frame, text="月度预算:").grid(row=2, column=0, sticky=tk.W, pady=5)
        budget_entry = ttk.Entry(left_frame, width=25)
        budget_entry.grid(row=2, column=1, pady=5)
        
        right_frame = ttk.LabelFrame(parent, text="我的账户", padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("账户ID", "账户名称", "余额", "月预算")
        account_tree = ttk.Treeview(right_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            account_tree.heading(col, text=col)
            account_tree.column(col, width=100)
        
        account_tree.pack(fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=account_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        account_tree.configure(yscrollcommand=scrollbar.set)
        
        def refresh_accounts():
            account_tree.delete(*account_tree.get_children())
            accounts = self.db.get_user_accounts(self.current_user['user_id'])
            for acc in accounts:
                budget = f"¥{acc[3]:.2f}" if acc[3] else "未设置"
                account_tree.insert("", tk.END, values=(acc[0], acc[1], f"¥{acc[2]:.2f}", budget))
        
        def create_account():
            name = account_name_entry.get()
            try:
                balance = float(balance_entry.get() or 0)
                budget = float(budget_entry.get()) if budget_entry.get() else None
            except ValueError:
                messagebox.showerror("错误", "金额格式不正确")
                return
            if not name:
                messagebox.showerror("错误", "请输入账户名称")
                return
            self.db.create_account(self.current_user['user_id'], name, balance, budget)
            messagebox.showinfo("成功", "账户创建成功")
            account_name_entry.delete(0, tk.END)
            balance_entry.delete(0, tk.END)
            budget_entry.delete(0, tk.END)
            refresh_accounts()
        
        ttk.Button(left_frame, text="创建账户", command=create_account).grid(row=3, column=0, columnspan=2, pady=20)
        refresh_accounts()
        ttk.Button(right_frame, text="刷新", command=refresh_accounts).pack(pady=5)
    
    def setup_bill_tab(self, parent):
        left_frame = ttk.LabelFrame(parent, text="添加账单", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(left_frame, text="选择账户:").grid(row=0, column=0, sticky=tk.W, pady=5)
        account_var = tk.StringVar()
        account_combo = ttk.Combobox(left_frame, textvariable=account_var, width=23, state="readonly")
        account_combo.grid(row=0, column=1, pady=5)
        
        ttk.Label(left_frame, text="类型:").grid(row=1, column=0, sticky=tk.W, pady=5)
        type_var = tk.StringVar(value="支出")
        type_frame = ttk.Frame(left_frame)
        type_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(left_frame, text="标签:").grid(row=2, column=0, sticky=tk.W, pady=5)
        tag_var = tk.StringVar()
        tag_combo = ttk.Combobox(left_frame, textvariable=tag_var, width=23, state="readonly")
        tag_combo.grid(row=2, column=1, pady=5)
        
        def update_tag_list():
            bill_type = type_var.get()
            tags = self.db.get_user_tags(self.current_user['user_id'], bill_type)
            tag_list = [f"{tag[0]}-{tag[1]}" for tag in tags]
            tag_combo['values'] = ['无标签'] + tag_list
            if tag_combo['values']:
                tag_combo.current(0)
        
        ttk.Radiobutton(type_frame, text="收入", variable=type_var, value="收入", command=update_tag_list).pack(side=tk.LEFT)
        ttk.Radiobutton(type_frame, text="支出", variable=type_var, value="支出", command=update_tag_list).pack(side=tk.LEFT)
        
        ttk.Label(left_frame, text="金额:").grid(row=3, column=0, sticky=tk.W, pady=5)
        amount_entry = ttk.Entry(left_frame, width=25)
        amount_entry.grid(row=3, column=1, pady=5)
        
        ttk.Label(left_frame, text="日期:").grid(row=4, column=0, sticky=tk.W, pady=5)
        date_entry = ttk.Entry(left_frame, width=25)
        date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        date_entry.grid(row=4, column=1, pady=5)
        
        ttk.Label(left_frame, text="备注:").grid(row=5, column=0, sticky=tk.W, pady=5)
        remark_entry = ttk.Entry(left_frame, width=25)
        remark_entry.grid(row=5, column=1, pady=5)
        
        right_frame = ttk.LabelFrame(parent, text="最近账单", padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("账单ID", "账户", "标签", "类型", "金额", "日期", "备注")
        bill_tree = ttk.Treeview(right_frame, columns=columns, show="headings", height=15)
        column_widths = {"账单ID": 60, "账户": 80, "标签": 80, "类型": 60, "金额": 80, "日期": 100, "备注": 120}
        for col in columns:
            bill_tree.heading(col, text=col)
            bill_tree.column(col, width=column_widths.get(col, 80))
        bill_tree.pack(fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=bill_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        bill_tree.configure(yscrollcommand=scrollbar.set)
        
        def load_accounts():
            accounts = self.db.get_user_accounts(self.current_user['user_id'])
            account_list = [f"{acc[0]}-{acc[1]}" for acc in accounts]
            account_combo['values'] = account_list
            if account_list:
                account_combo.current(0)
        
        def refresh_bills():
            bill_tree.delete(*bill_tree.get_children())
            bills = self.db.get_bills(self.current_user['user_id'])
            for bill in bills:
                display_bill = list(bill[:7])
                if display_bill[2] is None:
                    display_bill[2] = "无标签"
                if bill[7]:
                    display_bill[6] = f"[固定] {display_bill[6]}"
                bill_tree.insert("", tk.END, values=display_bill)
        
        def add_bill():
            if not account_var.get():
                messagebox.showerror("错误", "请选择账户")
                return
            account_id = int(account_var.get().split('-')[0])
            try:
                amount = float(amount_entry.get())
            except ValueError:
                messagebox.showerror("错误", "金额格式不正确")
                return
            bill_type = type_var.get()
            bill_date = date_entry.get()
            remark = remark_entry.get()
            tag_id = None
            if tag_var.get() and tag_var.get() != '无标签':
                tag_id = int(tag_var.get().split('-')[0])
            success, result = self.db.add_bill(
                self.current_user['user_id'], account_id, bill_type, amount, bill_date, tag_id, remark
            )
            if success:
                messagebox.showinfo("成功", "账单添加成功")
                amount_entry.delete(0, tk.END)
                remark_entry.delete(0, tk.END)
                date_entry.delete(0, tk.END)
                date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
                refresh_bills()
                load_accounts()
            else:
                messagebox.showerror("错误", f"添加失败: {result}")
        
        def delete_bill():
            selected = bill_tree.selection()
            if not selected:
                messagebox.showwarning("警告", "请选择要删除的账单")
                return
            bill_id = bill_tree.item(selected[0])['values'][0]
            if messagebox.askyesno("确认", "确定要删除这条账单吗?"):
                success, msg = self.db.delete_bill(bill_id)
                if success:
                    messagebox.showinfo("成功", msg)
                    refresh_bills()
                    load_accounts()
                else:
                    messagebox.showerror("错误", msg)
        
        load_accounts()
        update_tag_list()
        refresh_bills()
        ttk.Button(left_frame, text="添加账单", command=add_bill).grid(row=6, column=0, columnspan=2, pady=20)
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="刷新", command=refresh_bills).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="删除选中", command=delete_bill).pack(side=tk.LEFT)
    
    def setup_tag_tab(self, parent):
        left_frame = ttk.LabelFrame(parent, text="创建新标签", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(left_frame, text="标签名称:").grid(row=0, column=0, sticky=tk.W, pady=5)
        tag_name_entry = ttk.Entry(left_frame, width=25)
        tag_name_entry.grid(row=0, column=1, pady=5)
        
        ttk.Label(left_frame, text="标签类型:").grid(row=1, column=0, sticky=tk.W, pady=5)
        tag_type_var = tk.StringVar(value="支出")
        type_frame = ttk.Frame(left_frame)
        type_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Radiobutton(type_frame, text="收入", variable=tag_type_var, value="收入").pack(side=tk.LEFT)
        ttk.Radiobutton(type_frame, text="支出", variable=tag_type_var, value="支出").pack(side=tk.LEFT)
        
        ttk.Label(left_frame, text="标签颜色:").grid(row=2, column=0, sticky=tk.W, pady=5)
        color_var = tk.StringVar(value="#3498db")
        color_combo = ttk.Combobox(left_frame, textvariable=color_var, width=22, state="readonly")
        color_combo['values'] = ['#e74c3c', '#3498db', '#9b59b6', '#f39c12', '#1abc9c', 
                                  '#34495e', '#e67e22', '#27ae60', '#2ecc71', '#16a085']
        color_combo.grid(row=2, column=1, pady=5)
        
        right_frame = ttk.LabelFrame(parent, text="我的标签", padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("标签ID", "标签名称", "类型", "颜色")
        tag_tree = ttk.Treeview(right_frame, columns=columns, show="headings", height=15)
        for col in columns:
            tag_tree.heading(col, text=col)
            tag_tree.column(col, width=100)
        tag_tree.pack(fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=tag_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tag_tree.configure(yscrollcommand=scrollbar.set)
        
        def refresh_tags():
            tag_tree.delete(*tag_tree.get_children())
            tags = self.db.get_user_tags(self.current_user['user_id'])
            for tag in tags:
                tag_tree.insert("", tk.END, values=tag)
        
        def create_tag():
            tag_name = tag_name_entry.get()
            tag_type = tag_type_var.get()
            color = color_var.get()
            if not tag_name:
                messagebox.showerror("错误", "请输入标签名称")
                return
            success, result = self.db.create_tag(self.current_user['user_id'], tag_name, tag_type, color)
            if success:
                messagebox.showinfo("成功", "标签创建成功")
                tag_name_entry.delete(0, tk.END)
                refresh_tags()
            else:
                messagebox.showerror("错误", result)
        
        def delete_tag():
            selected = tag_tree.selection()
            if not selected:
                messagebox.showwarning("警告", "请选择要删除的标签")
                return
            tag_id = tag_tree.item(selected[0])['values'][0]
            if messagebox.askyesno("确认", "删除标签后，使用该标签的账单将变为无标签。\n确定要删除吗?"):
                success, msg = self.db.delete_tag(tag_id)
                if success:
                    messagebox.showinfo("成功", msg)
                    refresh_tags()
                else:
                    messagebox.showerror("错误", msg)
        
        def edit_tag():
            selected = tag_tree.selection()
            if not selected:
                messagebox.showwarning("警告", "请选择要修改的标签")
                return
            tag_id = tag_tree.item(selected[0])['values'][0]
            tag_name = tag_tree.item(selected[0])['values'][1]
            tag_color = tag_tree.item(selected[0])['values'][3]
            edit_window = tk.Toplevel(self.root)
            edit_window.title("修改标签")
            edit_window.geometry("300x200")
            frame = ttk.Frame(edit_window, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)
            ttk.Label(frame, text="标签名称:").grid(row=0, column=0, sticky=tk.W, pady=5)
            edit_name_entry = ttk.Entry(frame, width=20)
            edit_name_entry.insert(0, tag_name)
            edit_name_entry.grid(row=0, column=1, pady=5)
            ttk.Label(frame, text="标签颜色:").grid(row=1, column=0, sticky=tk.W, pady=5)
            edit_color_var = tk.StringVar(value=tag_color)
            edit_color_combo = ttk.Combobox(frame, textvariable=edit_color_var, width=17, state="readonly")
            edit_color_combo['values'] = ['#e74c3c', '#3498db', '#9b59b6', '#f39c12', '#1abc9c', 
                                          '#34495e', '#e67e22', '#27ae60', '#2ecc71', '#16a085']
            edit_color_combo.grid(row=1, column=1, pady=5)
            def save_edit():
                new_name = edit_name_entry.get()
                new_color = edit_color_var.get()
                if not new_name:
                    messagebox.showerror("错误", "标签名称不能为空")
                    return
                success, msg = self.db.update_tag(tag_id, new_name, new_color)
                if success:
                    messagebox.showinfo("成功", msg)
                    refresh_tags()
                    edit_window.destroy()
                else:
                    messagebox.showerror("错误", msg)
            ttk.Button(frame, text="保存", command=save_edit).grid(row=2, column=0, columnspan=2, pady=20)
        
        refresh_tags()
        ttk.Button(left_frame, text="创建标签", command=create_tag).grid(row=3, column=0, columnspan=2, pady=20)
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="刷新", command=refresh_tags).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="修改", command=edit_tag).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="删除", command=delete_tag).pack(side=tk.LEFT)
    
    def setup_recurring_tab(self, parent):
        left_frame = ttk.LabelFrame(parent, text="创建固定账单规则", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(left_frame, text="账户:").grid(row=0, column=0, sticky=tk.W, pady=5)
        account_var = tk.StringVar()
        account_combo = ttk.Combobox(left_frame, textvariable=account_var, width=23, state="readonly")
        account_combo.grid(row=0, column=1, pady=5)
        
        ttk.Label(left_frame, text="类型:").grid(row=1, column=0, sticky=tk.W, pady=5)
        type_var = tk.StringVar(value="支出")
        type_frame = ttk.Frame(left_frame)
        type_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(left_frame, text="标签:").grid(row=2, column=0, sticky=tk.W, pady=5)
        tag_var = tk.StringVar()
        tag_combo = ttk.Combobox(left_frame, textvariable=tag_var, width=23, state="readonly")
        tag_combo.grid(row=2, column=1, pady=5)
        
        def update_tag_list():
            bill_type = type_var.get()
            tags = self.db.get_user_tags(self.current_user['user_id'], bill_type)
            tag_list = [f"{tag[0]}-{tag[1]}" for tag in tags]
            tag_combo['values'] = ['无标签'] + tag_list
            if tag_combo['values']:
                tag_combo.current(0)
        
        ttk.Radiobutton(type_frame, text="收入", variable=type_var, value="收入", command=update_tag_list).pack(side=tk.LEFT)
        ttk.Radiobutton(type_frame, text="支出", variable=type_var, value="支出", command=update_tag_list).pack(side=tk.LEFT)
        
        ttk.Label(left_frame, text="金额:").grid(row=3, column=0, sticky=tk.W, pady=5)
        amount_entry = ttk.Entry(left_frame, width=25)
        amount_entry.grid(row=3, column=1, pady=5)
        
        ttk.Label(left_frame, text="频率:").grid(row=4, column=0, sticky=tk.W, pady=5)
        freq_var = tk.StringVar(value="每月")
        freq_combo = ttk.Combobox(left_frame, textvariable=freq_var, width=23, state="readonly")
        freq_combo['values'] = ['每日', '每周', '每月', '每年']
        freq_combo.grid(row=4, column=1, pady=5)
        
        ttk.Label(left_frame, text="开始日期:").grid(row=5, column=0, sticky=tk.W, pady=5)
        start_date_entry = ttk.Entry(left_frame, width=25)
        start_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        start_date_entry.grid(row=5, column=1, pady=5)
        
        ttk.Label(left_frame, text="结束日期:").grid(row=6, column=0, sticky=tk.W, pady=5)
        end_date_entry = ttk.Entry(left_frame, width=25)
        end_date_entry.grid(row=6, column=1, pady=5)
        ttk.Label(left_frame, text="(可选)", font=("Arial", 8)).grid(row=7, column=1, sticky=tk.W)
        
        ttk.Label(left_frame, text="每月第几天:").grid(row=8, column=0, sticky=tk.W, pady=5)
        day_of_month_entry = ttk.Entry(left_frame, width=25)
        day_of_month_entry.grid(row=8, column=1, pady=5)
        ttk.Label(left_frame, text="(每月频率时填1-31)", font=("Arial", 8)).grid(row=9, column=1, sticky=tk.W)
        
        ttk.Label(left_frame, text="备注:").grid(row=10, column=0, sticky=tk.W, pady=5)
        remark_entry = ttk.Entry(left_frame, width=25)
        remark_entry.grid(row=10, column=1, pady=5)
        
        right_frame = ttk.LabelFrame(parent, text="固定账单规则列表", padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("规则ID", "账户", "标签", "类型", "金额", "频率", "开始日期", "状态")
        rule_tree = ttk.Treeview(right_frame, columns=columns, show="headings", height=18)
        column_widths = {"规则ID": 50, "账户": 80, "标签": 70, "类型": 50, "金额": 70, "频率": 60, "开始日期": 90, "状态": 50}
        for col in columns:
            rule_tree.heading(col, text=col)
            rule_tree.column(col, width=column_widths.get(col, 80))
        rule_tree.pack(fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=rule_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        rule_tree.configure(yscrollcommand=scrollbar.set)
        
        def load_accounts():
            accounts = self.db.get_user_accounts(self.current_user['user_id'])
            account_list = [f"{acc[0]}-{acc[1]}" for acc in accounts]
            account_combo['values'] = account_list
            if account_list:
                account_combo.current(0)
        
        def refresh_rules():
            rule_tree.delete(*rule_tree.get_children())
            rules = self.db.get_recurring_rules(self.current_user['user_id'])
            for rule in rules:
                status = "启用" if rule[9] else "停用"
                display_rule = (rule[0], rule[1], rule[2] or "无标签", rule[3], 
                               f"¥{rule[4]:.2f}", rule[5], rule[6], status)
                rule_tree.insert("", tk.END, values=display_rule)
        
        def create_rule():
            if not account_var.get():
                messagebox.showerror("错误", "请选择账户")
                return
            account_id = int(account_var.get().split('-')[0])
            try:
                amount = float(amount_entry.get())
            except ValueError:
                messagebox.showerror("错误", "金额格式不正确")
                return
            bill_type = type_var.get()
            frequency = freq_var.get()
            start_date = start_date_entry.get()
            end_date = end_date_entry.get() if end_date_entry.get() else None
            remark = remark_entry.get()
            tag_id = None
            if tag_var.get() and tag_var.get() != '无标签':
                tag_id = int(tag_var.get().split('-')[0])
            day_of_month = None
            day_of_week = None
            if frequency == '每月':
                try:
                    day_of_month = int(day_of_month_entry.get())
                    if day_of_month < 1 or day_of_month > 31:
                        messagebox.showerror("错误", "每月第几天必须在1-31之间")
                        return
                except ValueError:
                    messagebox.showerror("错误", "每月频率时必须填写第几天(1-31)")
                    return
            elif frequency == '每周':
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                day_of_week = start_date_obj.weekday()
            success, result = self.db.create_recurring_rule(
                self.current_user['user_id'], account_id, bill_type, amount, frequency,
                start_date, tag_id, end_date, day_of_month, day_of_week, remark
            )
            if success:
                messagebox.showinfo("成功", f"固定账单规则创建成功！\n系统将自动在每个{frequency}执行")
                amount_entry.delete(0, tk.END)
                remark_entry.delete(0, tk.END)
                day_of_month_entry.delete(0, tk.END)
                end_date_entry.delete(0, tk.END)
                start_date_entry.delete(0, tk.END)
                start_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
                refresh_rules()
            else:
                messagebox.showerror("错误", f"创建失败: {result}")
        
        def toggle_rule():
            selected = rule_tree.selection()
            if not selected:
                messagebox.showwarning("警告", "请选择要操作的规则")
                return
            rule_id = rule_tree.item(selected[0])['values'][0]
            current_status = rule_tree.item(selected[0])['values'][7]
            new_status = current_status == "停用"
            action = "启用" if new_status else "停用"
            if messagebox.askyesno("确认", f"确定要{action}这条规则吗?"):
                self.db.toggle_recurring_rule(rule_id, new_status)
                messagebox.showinfo("成功", f"规则已{action}")
                refresh_rules()
        
        def delete_rule():
            selected = rule_tree.selection()
            if not selected:
                messagebox.showwarning("警告", "请选择要删除的规则")
                return
            rule_id = rule_tree.item(selected[0])['values'][0]
            if messagebox.askyesno("确认", "删除规则不会删除已生成的账单\n确定要删除吗?"):
                success, msg = self.db.delete_recurring_rule(rule_id)
                if success:
                    messagebox.showinfo("成功", msg)
                    refresh_rules()
                else:
                    messagebox.showerror("错误", msg)
        
        def manual_execute():
            count = self.db.execute_recurring_bills()
            if count > 0:
                messagebox.showinfo("成功", f"成功生成了 {count} 条固定账单")
                refresh_rules()
            else:
                messagebox.showinfo("提示", "今天没有需要执行的固定账单")
        
        load_accounts()
        update_tag_list()
        refresh_rules()
        ttk.Button(left_frame, text="创建规则", command=create_rule).grid(row=11, column=0, columnspan=2, pady=20)
        button_frame = ttk.Frame(right_frame)   
        button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="刷新", command=refresh_rules).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="启用/停用", command=toggle_rule).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="删除规则", command=delete_rule).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="手动执行", command=manual_execute).pack(side=tk.LEFT, padx=5)

    def setup_query_tab(self, parent):
        query_frame = ttk.LabelFrame(parent, text="查询条件", padding="10")
        query_frame.pack(fill=tk.X, padx=5, pady=5)
        
        row1 = ttk.Frame(query_frame)
        row1.pack(fill=tk.X, pady=5)
        ttk.Label(row1, text="账户:").pack(side=tk.LEFT, padx=5)
        account_var = tk.StringVar()
        account_combo = ttk.Combobox(row1, textvariable=account_var, width=15, state="readonly")
        account_combo.pack(side=tk.LEFT, padx=5)
        ttk.Label(row1, text="标签:").pack(side=tk.LEFT, padx=5)
        tag_var = tk.StringVar()
        tag_combo = ttk.Combobox(row1, textvariable=tag_var, width=15, state="readonly")
        tag_combo.pack(side=tk.LEFT, padx=5)
        ttk.Label(row1, text="类型:").pack(side=tk.LEFT, padx=5)
        type_var = tk.StringVar()
        type_combo = ttk.Combobox(row1, textvariable=type_var, width=10, state="readonly")
        type_combo['values'] = ['全部', '收入', '支出']
        type_combo.current(0)
        type_combo.pack(side=tk.LEFT, padx=5)
        
        row2 = ttk.Frame(query_frame)
        row2.pack(fill=tk.X, pady=5)
        ttk.Label(row2, text="开始日期:").pack(side=tk.LEFT, padx=5)
        start_date_entry = ttk.Entry(row2, width=12)
        start_date_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(row2, text="结束日期:").pack(side=tk.LEFT, padx=5)
        end_date_entry = ttk.Entry(row2, width=12)
        end_date_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(row2, text="(格式: YYYY-MM-DD)").pack(side=tk.LEFT, padx=5)
        
        result_frame = ttk.LabelFrame(parent, text="查询结果", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        stats_frame = ttk.Frame(result_frame)
        stats_frame.pack(fill=tk.X, pady=5)
        income_label = ttk.Label(stats_frame, text="收入: ¥0.00", foreground="green")
        income_label.pack(side=tk.LEFT, padx=20)
        expense_label = ttk.Label(stats_frame, text="支出: ¥0.00", foreground="red")
        expense_label.pack(side=tk.LEFT, padx=20)
        balance_label = ttk.Label(stats_frame, text="结余: ¥0.00")
        balance_label.pack(side=tk.LEFT, padx=20)
        count_label = ttk.Label(stats_frame, text="记录数: 0")
        count_label.pack(side=tk.LEFT, padx=20)
        
        columns = ("账单ID", "账户", "标签", "类型", "金额", "日期", "备注")
        result_tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=16)
        column_widths = {"账单ID": 60, "账户": 90, "标签": 90, "类型": 60, "金额": 80, "日期": 100, "备注": 150}
        for col in columns:
            result_tree.heading(col, text=col)
            result_tree.column(col, width=column_widths.get(col, 80))
        result_tree.pack(fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=result_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        result_tree.configure(yscrollcommand=scrollbar.set)
        
        def load_filter_options():
            accounts = self.db.get_user_accounts(self.current_user['user_id'])
            account_list = ['全部'] + [f"{acc[0]}-{acc[1]}" for acc in accounts]
            account_combo['values'] = account_list
            account_combo.current(0)
            tags = self.db.get_user_tags(self.current_user['user_id'])
            tag_list = ['全部'] + [f"{tag[0]}-{tag[1]}" for tag in tags]
            tag_combo['values'] = tag_list
            tag_combo.current(0)
        
        def query_bills():
            account_id = None
            if account_var.get() and account_var.get() != '全部':
                account_id = int(account_var.get().split('-')[0])
            tag_id = None
            if tag_var.get() and tag_var.get() != '全部':
                tag_id = int(tag_var.get().split('-')[0])
            bill_type = None
            if type_var.get() != '全部':
                bill_type = type_var.get()
            start_date = start_date_entry.get() if start_date_entry.get() else None
            end_date = end_date_entry.get() if end_date_entry.get() else None
            bills = self.db.get_bills(self.current_user['user_id'], account_id=account_id, tag_id=tag_id,
                                      start_date=start_date, end_date=end_date, bill_type=bill_type)
            result_tree.delete(*result_tree.get_children())
            total_income = 0
            total_expense = 0
            for bill in bills:
                display_bill = list(bill[:7])
                if display_bill[2] is None:
                    display_bill[2] = "无标签"
                if bill[7]:
                    display_bill[6] = f"[固定] {display_bill[6]}"
                result_tree.insert("", tk.END, values=display_bill)
                if bill[3] == '收入':
                    total_income += bill[4]
                else:
                    total_expense += bill[4]
            income_label.config(text=f"收入: ¥{total_income:.2f}")
            expense_label.config(text=f"支出: ¥{total_expense:.2f}")
            balance_label.config(text=f"结余: ¥{total_income - total_expense:.2f}")
            count_label.config(text=f"记录数: {len(bills)}")
        
        def export_query_result():
            items = result_tree.get_children()
            if not items:
                messagebox.showwarning("警告", "没有数据可导出")
                return
            filename = f"账单查询结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("账单查询结果\n")
                f.write("="*80 + "\n")
                f.write(f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{income_label.cget('text')} | {expense_label.cget('text')} | {balance_label.cget('text')}\n")
                f.write("="*80 + "\n\n")
                for item in items:
                    values = result_tree.item(item)['values']
                    f.write(f"账单ID: {values[0]}\n")
                    f.write(f"账户: {values[1]} | 标签: {values[2]} | 类型: {values[3]}\n")
                    f.write(f"金额: ¥{values[4]} | 日期: {values[5]}\n")
                    f.write(f"备注: {values[6]}\n")
                    f.write("-"*80 + "\n")
            messagebox.showinfo("成功", f"结果已导出到: {filename}")
        
        load_filter_options()
        button_frame = ttk.Frame(query_frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="查询", command=query_bills).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重置", command=lambda: [
            account_combo.current(0), tag_combo.current(0), type_combo.current(0),
            start_date_entry.delete(0, tk.END), end_date_entry.delete(0, tk.END),
            result_tree.delete(*result_tree.get_children()),
            income_label.config(text="收入: ¥0.00"), expense_label.config(text="支出: ¥0.00"),
            balance_label.config(text="结余: ¥0.00"), count_label.config(text="记录数: 0")
        ]).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="导出结果", command=export_query_result).pack(side=tk.LEFT, padx=5)
    
    def setup_stats_tab(self, parent):
        time_frame = ttk.LabelFrame(parent, text="统计时间范围", padding="10")
        time_frame.pack(fill=tk.X, padx=5, pady=5)
        
        row1 = ttk.Frame(time_frame)
        row1.pack(fill=tk.X, pady=5)
        ttk.Label(row1, text="开始日期:").pack(side=tk.LEFT, padx=5)
        start_date_entry = ttk.Entry(row1, width=12)
        start_date_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(row1, text="结束日期:").pack(side=tk.LEFT, padx=5)
        end_date_entry = ttk.Entry(row1, width=12)
        end_date_entry.pack(side=tk.LEFT, padx=5)
        
        def set_this_month():
            now = datetime.now()
            start = now.strftime('%Y-%m-01')
            end = now.strftime('%Y-%m-%d')
            start_date_entry.delete(0, tk.END)
            start_date_entry.insert(0, start)
            end_date_entry.delete(0, tk.END)
            end_date_entry.insert(0, end)
        
        def set_last_month():
            now = datetime.now()
            if now.month == 1:
                start = f"{now.year-1}-12-01"
                end = f"{now.year-1}-12-31"
            else:
                start = f"{now.year}-{now.month-1:02d}-01"
                last_day = calendar.monthrange(now.year, now.month-1)[1]
                end = f"{now.year}-{now.month-1:02d}-{last_day}"
            start_date_entry.delete(0, tk.END)
            start_date_entry.insert(0, start)
            end_date_entry.delete(0, tk.END)
            end_date_entry.insert(0, end)
        
        ttk.Button(row1, text="本月", command=set_this_month).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="上月", command=set_last_month).pack(side=tk.LEFT, padx=5)
        
        overview_frame = ttk.LabelFrame(parent, text="统计概览", padding="10")
        overview_frame.pack(fill=tk.X, padx=5, pady=5)
        stats_display = ttk.Frame(overview_frame)
        stats_display.pack(fill=tk.X, pady=10)
        income_stat = ttk.Label(stats_display, text="总收入: ¥0.00", font=("Arial", 14), foreground="green")
        income_stat.pack(side=tk.LEFT, padx=30)
        expense_stat = ttk.Label(stats_display, text="总支出: ¥0.00", font=("Arial", 14), foreground="red")
        expense_stat.pack(side=tk.LEFT, padx=30)
        balance_stat = ttk.Label(stats_display, text="结余: ¥0.00", font=("Arial", 14))
        balance_stat.pack(side=tk.LEFT, padx=30)
        
        detail_frame = ttk.LabelFrame(parent, text="分类统计", padding="10")
        detail_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        expense_frame = ttk.Frame(detail_frame)
        expense_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        ttk.Label(expense_frame, text="支出分类", font=("Arial", 12, "bold")).pack(pady=5)
        expense_columns = ("标签", "金额", "占比")
        expense_tree = ttk.Treeview(expense_frame, columns=expense_columns, show="headings", height=10)
        for col in expense_columns:
            expense_tree.heading(col, text=col)
            expense_tree.column(col, width=100)
        expense_tree.pack(fill=tk.BOTH, expand=True)
        
        income_frame = ttk.Frame(detail_frame)
        income_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        ttk.Label(income_frame, text="收入分类", font=("Arial", 12, "bold")).pack(pady=5)
        income_columns = ("标签", "金额", "占比")
        income_tree = ttk.Treeview(income_frame, columns=income_columns, show="headings", height=10)
        for col in income_columns:
            income_tree.heading(col, text=col)
            income_tree.column(col, width=100)
        income_tree.pack(fill=tk.BOTH, expand=True)
        
        def generate_stats():
            start_date = start_date_entry.get() if start_date_entry.get() else None
            end_date = end_date_entry.get() if end_date_entry.get() else None
            stats = self.db.get_bill_statistics(self.current_user['user_id'], start_date, end_date)
            income_stat.config(text=f"总收入: ¥{stats['total_income']:.2f}")
            expense_stat.config(text=f"总支出: ¥{stats['total_expense']:.2f}")
            balance_stat.config(text=f"结余: ¥{stats['balance']:.2f}")
            expense_tree.delete(*expense_tree.get_children())
            total_expense = stats['total_expense']
            for tag_name, amount in stats['expense_by_tag']:
                tag_display = tag_name if tag_name else "无标签"
                percentage = (amount / total_expense * 100) if total_expense > 0 else 0
                expense_tree.insert("", tk.END, values=(tag_display, f"¥{amount:.2f}", f"{percentage:.1f}%"))
            income_tree.delete(*income_tree.get_children())
            total_income = stats['total_income']
            for tag_name, amount in stats['income_by_tag']:
                tag_display = tag_name if tag_name else "无标签"
                percentage = (amount / total_income * 100) if total_income > 0 else 0
                income_tree.insert("", tk.END, values=(tag_display, f"¥{amount:.2f}", f"{percentage:.1f}%"))
        
        ttk.Button(time_frame, text="生成统计", command=generate_stats).pack(side=tk.LEFT, padx=10)
        set_this_month()
        generate_stats()
    
    def show_user_info(self):
        info_window = tk.Toplevel(self.root)
        info_window.title("个人信息管理")
        info_window.geometry("400x300")
        frame = ttk.Frame(info_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="个人信息管理", font=("Arial", 16, "bold")).pack(pady=20)
        ttk.Label(frame, text=f"用户名: {self.current_user['username']}").pack(pady=5)
        ttk.Label(frame, text="修改手机号:").pack(pady=5)
        phone_entry = ttk.Entry(frame, width=30)
        phone_entry.pack(pady=5)
        ttk.Label(frame, text="新密码:").pack(pady=5)
        password_entry = ttk.Entry(frame, width=30, show="*")
        password_entry.pack(pady=5)
        
        def update_info():
            phone = phone_entry.get()
            password = password_entry.get()
            if not phone and not password:
                messagebox.showwarning("警告", "请至少填写一项")
                return
            success = self.db.update_user_info(
                self.current_user['user_id'],
                phone if phone else None,
                password if password else None
            )
            if success:
                messagebox.showinfo("成功", "信息更新成功")
                info_window.destroy()
            else:
                messagebox.showerror("错误", "更新失败")
        
        ttk.Button(frame, text="更新信息", command=update_info).pack(pady=20)
    
    def run(self):
        self.root.mainloop()



if __name__ == '__main__':
    app = AccountingApp()
    app.run()
# Test
# Test
# CI test
# CI test
