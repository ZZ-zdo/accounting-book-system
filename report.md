# 实验五：软件测试与修复

### 赵雪东 231220011



## 一、单元测试报告

**1.测试目的**

单元测试的目的是在开发阶段对代码的最小可测试单元（如函数、方法或类）进行验证，以尽早发现和修复缺陷，确保代码按预期工作，同时为代码重构提供安全保障，促进更好的代码设计和模块化，并通过自动化测试提高开发效率和代码质量，最终降低软件维护成本并增强团队对代码的信心。

**2.测试过程**

我选择用pytest进行单元测试，对项目的用户管理功能模块和账单管理功能模块两个模块进行测试。下面将分别介绍两个模块的测试。

**2.1用户管理模块测试**

我选择采用判定覆盖来对该模块进行测试，每个判定的真假分支都执行一次。

|测试用例编号|测试目的|输入数据|预期结果 |实际输出|测试结果 |
| :----------: | :------------: | :----------: | :--------: | :------------: | :------------: |
|1|测试成功注册新用户|username="test_user"<br>password="password123"|注册成功|注册成功|succeed|
|2|测试用户名已存在|username="test_user"<br>password="password123"|注册失败且返回用户名已存在|注册成功|failed|
|3|测试空密码应该失败|username="newuser"<br>password=""|注册失败|注册成功|failed|
|4|测试空用户名应该失败|username=""<br>password="password123"|注册失败|注册成功|failed|
|5|测试注册时提供手机号|username="phoneuser"<br>password="password123"<br>phone="1234567890"|注册成功|注册成功|succeed|
|6|测试用户名包含特殊字符|username="user@123"<br>password="password123"|注册成功|注册成功|succeed|
|7|测试单字符用户名	|username="a"<br>password="password123"|注册成功|注册成功|succeed|
|8|测试超长用户名|username="a"*256<br>password="password123"|注册失败|注册成功|failed|
|9|测试超长密码|username="newuser"<br>password="a"*256|注册失败|注册成功|failed|
|10|测试特殊格式的手机|username="newphoneuser"<br>password="password123"<br>phone="123-456-7890"|注册失败|注册成功|failed|

测试结果：

![alt text](image-3.png)

![alt text](image-4.png)

![alt text](image-5.png)

可以看到在用户注册模块没有对用户名和密码为空的情况作处理，没有限制用户名和密码的长度，也没有检查手机号码的格式，也没有对重复注册的用户名做处理，缺陷很多。

**2.2账单管理功能测试**
  
我选择采用判定覆盖来对该模块进行测试，每个判定的真假分支都执行一次。

| 测试用例编号 |  测试目的 |输入数据| 预期结果|备注 |测试结果|
| :------------: | :-----: |:---: | :-----: | :------: | :---: |
| 01| 正常添加支出账单 | bill_type='支出'<br>amount=150.0<br>bill_date='2025-12-12'<br>remark='测试支出' | success=True<br>返回bill_id<br>余额减少150 | 验证余额变化和账单存储 |succeed|
| 02| 正常添加收入账单| bill_type='收入'<br>amount=5000.0<br>bill_date='2025-12-01'<br>remark='月工资'| success=True<br>返回bill_id<br>余额增加5000|  大额收入测试 |succeed|
|03| 添加带标签的账单| bill_type='支出'<br>amount=88.0<br>tag_id=有效标签ID<br>remark='午餐'| success=True<br>标签正确关联<br>可通过tag_id查询 |  验证标签关联功能       |succeed|
|04|  添加金额为0的账单          | bill_type='支出'<br>amount=0.0<br>bill_date='2025-12-12'                                                                    | success=True/False<br>余额不变或报错             |  业务逻辑决定是否允许   |succeed|
|05| 添加负数金额账单           | bill_type='支出'<br>amount=-100.0<br>bill_date='2025-12-12'                                                                 | success=False<br>或特殊处理                      |  异常输入测试           |succeed|
|06| 使用不存在的账户ID         | account_id=99999<br>amount=50.0<br>bill_type='支出'                                                                         | success=False<br>返回错误消息                    |  数据库约束验证         |failed|
|07| 成功删除支出账单并恢复余额 | 先添加支出账单amount=200<br>再删除该账单 | success=True<br>余额增加200<br>账单已删除        |  验证余额回滚机制       |succeed|
| 08| 删除收入账单并扣减余额     | 先添加收入账单amount=1000<br>再删除该账单| success=True<br>余额减少1000<br>账单已删除       |  收入删除的余额处理     |succeed|
|09|删除不存在的账单           | bill_id=99999| success=False<br>message包含"不存在"             |  无效ID处理             |succeed|
| 10     | 综合查询-多条件筛选        | 场景1: 无过滤<br>场景2: 按账户<br>场景3: 按日期范围<br>场景4: 按类型<br>场景5: 按标签<br>场景6: 复合条件<br>场景7: 排序验证 | 各场景返回正确数量和内容的账单列表               | 测试查询功能完整性     |succeed|
| 11     | 超长备注字段               | remark="测"*1000<br>(1000个字符)                                                                                            | success=True或False<br>备注正确存储或被拒绝      |  Bonus测试              |succeed|
| 12     | 无效日期格式               | bill_date='12/12/2025'<br>(错误格式) | 可能成功或失败                                   |  SQLite日期宽松性测试   |succeed|
| 13     | 预算警告触发 | 连续添加支出:  <br>2000+2000+500=4500<br>(超过月预算5000的90%)| success=True<br>触发预算警告<br>本月支出>=4500   |  需要mock messagebox    |succeed|
、
测试结果：

![alt text](image-6.png)

![alt text](image-7.png)

从测试结果可以看出，添加账单的时候没有检查账户ID是否存在。


* 2.3覆盖率说明

测试一覆盖率为100%，测试二覆盖率大约为90%，没有对和添加标签的分支进行测试。

## 二、集成测试报告

**1.测试目的**
本项目集成测试的目的是验证记账本系统中用户管理、账户管理、账单管理、标签管理、统计分析等模块在实际协作时能否正确完成完整的业务流程。通过自顶向下和自底向上两种集成策略，测试从用户注册登录到记账、查询、统计的全流程，重点验证模块间的数据传递（如账单添加后账户余额的自动更新）、外键约束（如标签删除时关联账单的处理）、事务一致性（如固定账单的自动生成）等关键集成点，确保各模块组合后能为用户提供完整、可靠的记账服务。

**2.测试过程**
集成测试我使用了pytest，使用了三种集成测试方法，分别是自顶向下、自底向上和跨模块边界测试。自顶向下测试涉及的模块有用户管理、账户管理、标签管理、账单管理、统计分析模块，模拟了完整的业务流程。自底向上测试有两个，分别为对账单-标签关系完整性测试和对固定账单自动处理的测试。跨模块边界测试针对账户删除对账单的影响做了测试。所有测试全部通过

![alt text](image-8.png)




![alt text](image-9.png)

![alt text](image-10.png)

## 三、模糊测试报告

**1.模糊测试工具安装**
我使用的模糊测试工具是atheris，系统为ubuntu。在ubuntu系统中安装atheris需要创建虚拟环境，在虚拟环境中安装。下图表示安装成功。

![alt text](image-11.png)

**2.测试目标**
- register_user() - 用户注册
- add_bill() - 账单添加  
- get_bills() - 账单查询
- hash_password() - 密码哈希

运行过程截图

![alt text](image-12.png)

**3.测试结果**
我先是简单的测试了十分钟，没有出现崩溃，然后使用指令timeout 18000 python fuzz_test.py指定运行时间为五个小时，运行之后还是没有崩溃。可能原因是我的项目代码中所有关键操作都使用了 try-except 异常捕获，这会有效防止崩溃发生。而且代码使用了 SQLite 的参数化查询，有效防止了 SQL 注入攻击。另外Python 是内存安全的语言，自动管理内存，不存在空指针等问题。

## 四、持续集成报告

**1.工作流文件内容**

当项目代码被push到仓库中时，会自动进行两个单元测试和一个集成测试。

```
# .github/workflows/ci.yml

name: Python CI

# 触发条件
on:
  push: 
    branches: [ main, master, develop ]  # 推送到这些分支时触发
  pull_request: 
    branches: [ main, master, develop ]  # PR 到这些分支时触发

# 任务定义
jobs: 
  test: 
    name: Run Tests
    runs-on: ubuntu-latest  # 使用 Ubuntu 最新版本
    
    strategy:
      fail-fast: false  # 一个版本失败不影响其他版本
      matrix:
        python-version:  ['3.10', '3.11', '3.12']  # 测试多个 Python 版本
    
    steps:
    # 1. 检出代码
    - name: Checkout code
      uses:  actions/checkout@v4
    
    # 2. 设置 Python 环境
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix. python-version }}
    
    # 3. 缓存依赖（加速构建）
    - name: Cache pip packages
      uses: actions/cache@v3
      with: 
        path:  ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('requirements. txt') }}
        restore-keys: |
          ${{ runner. os }}-pip-
    
    # 4. 安装依赖
    - name:  Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pytest pytest-cov
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
    
    # 5. 运行单元测试
    - name:  Run unit tests
      run: |
        pytest register_test.py -v --tb=short
    
    # 6. 运行集成测试
    - name: Run integration tests
      run: |
        pytest test_integration.py -v --tb=short
    
    # 7. 运行账单管理测试
    - name: Run bill management tests
      run: |
        pytest bill_test.py -v --tb=short
```

**2.触发过程**

为了让GitHub Actions 成功运行首先得改好代码保证代码能够通过单元测试。改好代码后可以看到最新一次GitHub Actions运行成功了。

![alt text](image-18.png)

下面这个界面可以看到总共进行了三次测试，这三次测试每一次都运行了一遍两个单元测试和一个集成测试，三次测试均通过。

![alt text](image-17.png)

下图展示了每一次测试中都做了什么，这个流程就是ci.yml文件设置的流程，首先是运行前的环境设置，安装依赖，然后开始运行三个测试，最后清理临时文件。


![alt text](image-15.png)

## 五、程序修复报告

**1.AI助手**
使用的Github copilot

![alt text](image-14.png)

**2.修复的缺陷**
我修复的是本次实验中单元测试发现的缺陷，两个是用户管理模块的问题，注册用户名和密码的长度问题和注册电话号码的格式问题，另一个是账单管理模块中添加账单时账户ID不存在的问题，这三个问题是前面单元测试发现的。这三个缺陷比较简单，所以我直接向copilot描述问题询问如何修复这三个缺陷，因为copilot可以直接读我的代码，所以也不需要向他描述相关的上下文。下面是我向copilot提问的截图。


<img src="image-19.png" alt="测试结果" width="25%" /> <img src="image-20.png" alt="测试结果" width="25%" /> <img src="image-21.png" alt="测试结果" width="25%" />

因为这三个缺陷都是小问题，所以copilot的回答可以直接解决问题。把copilot回答的方案加到项目代码中进行测试，测试通过。修复添加的新代码如下

![alt text](image-22.png)

![alt text](image-23.png)

修复后的正确性验证如下，重新进行单元测试，全部通过

![alt text](image-25.png)

![alt text](image-24.png)

大模型的能力越来越强大，它的对代码的检查和修改能力也越来越强，结合实验四来看它可以处理大部分的问题并且效果比一些专门的工具还要好。使用大模型做代码检测并辅助开发将会大大提高效率。但是大模型并不总是正确的，本项目的代码量少，所以大模型表现出色，但是对于代码量巨大的项目来说，大模型的表现能力无法得到保证，还是要运用多种工具汇总结果进行对比，理性使用大模型。
