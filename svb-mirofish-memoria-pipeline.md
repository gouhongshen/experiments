# SVB 危机回放：多 Agent 辩论 × Memoria 分支推演

> 用 2023 年 3 月 SVB 银行挤兑的历史数据，让 12 个不同视角的 LLM Agent
> 在每个关键时间节点辩论、预测、分叉，全过程的认知状态由 Memoria 管理。
> `python main.py` 一键运行，约 1-2 小时出结果。前提：Memoria 服务已启动（见 §2.4）。

## 涉及的开源项目

| 项目 | 用途 | GitHub |
|------|------|--------|
| **Memoria** | 带版本控制的 Agent 记忆系统（branch / snapshot / rollback） | https://github.com/matrixorigin/Memoria |
| **MatrixOne** | Memoria 存储后端（向量 + 关系数据库） | https://github.com/matrixorigin/matrixone |
| **gdeltdoc** | GDELT 新闻事件 Python 客户端 | https://github.com/alex9smith/gdelt-doc-api |
| **yfinance** | Yahoo Finance 历史市场数据 | https://github.com/ranaroussi/yfinance |

---

## 目录

1. [概述与架构](#1-概述与架构)
2. [环境与配置](#2-环境与配置)
3. [数据准备](#3-数据准备)
4. [多 Agent 人设](#4-多-agent-人设)
5. [Memoria 客户端](#5-memoria-客户端)
6. [主循环 Orchestrator](#6-主循环-orchestrator)
7. [置信度与校准](#7-置信度与校准)
8. [输出与一键运行](#8-输出与一键运行)

---

## 1. 概述与架构

### 为什么不用仿真引擎

传统方案（如 MiroFish）需要额外搭建仿真环境，增加了不确定性和工程成本。
本方案直接用 LLM 扮演多个不同背景的分析师，对同一组真实历史数据进行独立判断。
当 Agent 群体出现显著分歧时，系统自动触发分叉——**分叉点不是预设的，而是从分歧中涌现的**。

**Memoria 是唯一主角**：所有认知状态、分叉、归档、校准都在 Memoria 中完成。

### 核心流程

```
每个时间步（T=0 到 T=6）：

  ┌──────────┐     ┌─────────────────────────┐     ┌───────────────┐
  │ 历史数据  │────▶│  12 个 Agent 独立分析    │────▶│  Orchestrator │
  │ (种子)    │     │  输出：判断 + 置信度     │     │  汇总 + 决策  │
  └──────────┘     └─────────────────────────┘     └───────┬───────┘
                                                           │
                                      ┌────────────────────┼────────────────────┐
                                      ▼                    ▼                    ▼
                                  继续推进             创建分叉              归档 Branch
                                  (update)          (branch+snapshot)     (archive+calibrate)
                                      │                    │                    │
                                      └────────────────────┴────────────────────┘
                                                           │
                                                    ┌──────▼──────┐
                                                    │   Memoria   │
                                                    │  /v1/...    │
                                                    └─────────────┘
```

### 时间步映射

```
真实时间              步骤    关键事件
──────────────────────────────────────────────────────
2023-03-08 EOD    →  T=0    SVB 公告债券亏损 18 亿
2023-03-09 09:30  →  T=1    股价 -60%，融资失败
2023-03-09 15:00  →  T=2    Founders Fund 建议提款 → 分歧可能涌现
2023-03-09 EOD    →  T=3    $42B 提款，交易暂停
2023-03-10 09:30  →  T=4    融资彻底失败
2023-03-10 15:00  →  T=5    FDIC 接管 → 分歧可能涌现
2023-03-12        →  T=6    Signature Bank 倒闭
```

### Branch 演化（涌现式 · 不预设分叉点）

> **核心变化**：分叉不再硬编码在 T2 / T5，而是当 Agent 投票出现
> 显著极化（信心差 ≥ 40 且标准差 ≥ 15）时自动触发。
> 每个分叉可产生 2-4 个子分支（按 contagion_risk 聚类），
> 活跃分支上限 8 条，防止指数爆炸。

以下是一次**可能**的运行结果示意（每次运行因 LLM 采样不同而异）：

```
T=0 ●───── main ─────────────────────────────────────────────
    │      12 Agent 意见较一致，无分叉
    │
T=1 ●───── main ─────────────────────────────────────────────
    │      股价暴跌，极化指数 38 < 阈值，仍无分叉
    │
T=2 ●───── main ─ 分歧涌现！极化 55、标准差 22、3 个派系
    │      ├── main_low（风险可控派 · 3 人）
    │      ├── main_medium（谨慎观望派 · 5 人）
    │      └── main_high（危机扩散派 · 4 人）
    │
T=3 ●───── main_low ·····✗ 信心 12% → 归档，校准沉淀
    │      main_medium ──────────────────────────────────────
    │      main_high ────────────────────────────────────────
    │
T=5 ●───── main_high ─ 再次分歧！FDIC 效果存疑
    │      ├── main_high_medium（FDIC够用）
    │      └── main_high_critical（系统性崩溃）
    │      main_medium ──────────────────────────────────────
    │
T=6 ●───── 幸存分支进入验证 → 优胜者合并回 main
```

---

## 2. 环境与配置

### 2.1 安装依赖

```bash
pip install requests pandas yfinance gdeltdoc python-dotenv
```

### 2.2 目录结构

```
svb-pipeline/
├── .env
├── config.py
├── data/
│   ├── fetch_gdelt.py
│   ├── fetch_market.py
│   ├── key_events.py
│   ├── build_seeds.py
│   └── timesteps/          # 自动生成
├── agents/
│   ├── personas.py         # 12 个 Agent 人设
│   └── llm_agent.py        # LLM 调用接口
├── memoria/
│   └── client.py           # Memoria REST + MCP 适配器
├── events/
│   └── recorder.py         # 结构化事件记录器
├── orchestrator/
│   └── main_loop.py        # 主循环 + 分叉决策 + 置信度追踪
├── calibration/
│   ├── scorer.py           # 信心聚合
│   ├── ground_truth.py     # 事后验证 + 自动评分
│   ├── rollback_experiment.py  # Memoria 回溯实验
│   └── epilogue.py         # 胜出分支 merge 回主线
├── output/
│   ├── dashboard.py              # 交互式叙事 Dashboard 生成器
│   └── _dashboard_template.html  # Dashboard HTML 模板
└── main.py
```

### 2.3 环境变量

```bash
# .env

# LLM（用于 Agent 分析 + Orchestrator 决策）
LLM_API_KEY=sk-...
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus

# Memoria REST API（必须与 client.py 和 main.py 一致，默认端口 3100）
MEMORIA_URL=http://localhost:3100

# 可选：国内 Yahoo Finance 代理
# HTTPS_PROXY=http://127.0.0.1:7890
```

### 2.4 启动 Memoria

```bash
# 按 Memoria 官方仓库部署，启动时需同时开启 HTTP transport（port 3100）
# 服务会同时暴露 REST /v1/... 和 MCP-over-HTTP /message 两个入口
# 验证：
curl -s http://localhost:3100/v1/branches | python3 -m json.tool
```

### 2.5 全局配置

```python
# config.py
import os
from dotenv import load_dotenv
load_dotenv()

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus")
MEMORIA_URL = os.getenv("MEMORIA_URL", "http://localhost:3100")

TIMESTEPS = [
    {"id": "T0", "real_time": "2023-03-08 16:00", "label": "SVB公告债券亏损"},
    {"id": "T1", "real_time": "2023-03-09 09:30", "label": "股价-60%，融资失败"},
    {"id": "T2", "real_time": "2023-03-09 15:00", "label": "Founders Fund提款建议"},
    {"id": "T3", "real_time": "2023-03-09 18:00", "label": "$42B提款请求"},
    {"id": "T4", "real_time": "2023-03-10 09:30", "label": "融资彻底失败"},
    {"id": "T5", "real_time": "2023-03-10 15:00", "label": "FDIC接管"},
    {"id": "T6", "real_time": "2023-03-12 12:00", "label": "Signature Bank倒闭"},
]

## ── 涌现式分叉检测（替代硬编码 FORK_RULES） ──
# 当 Agent 投票出现显著分歧时自动触发分叉，不再预定义"哪个时间步必须分叉"

FORK_POLARIZATION_THRESHOLD = 40   # max-min 信心差 ≥ 此值才考虑分叉
FORK_STD_THRESHOLD = 15            # 信心标准差 ≥ 此值才考虑分叉
MAX_ACTIVE_BRANCHES = 8            # 活跃分支上限，防止指数爆炸
MIN_CLUSTER_SIZE = 2               # 至少 2 个 Agent 持同一立场才形成派系

ARCHIVE_THRESHOLD = 20             # 共识信心低于此值的分支被归档（百分制）
```

---

## 3. 数据准备

### 3.1 新闻数据（GDELT）

```python
# data/fetch_gdelt.py
from gdeltdoc import GdeltDoc, Filters
import json, os
import pandas as pd

gd = GdeltDoc()

# 每个时间步对应的新闻截止窗口（东部时间，严格无前视）
# T1/T2/T3 同在 3月9日，通过关键词差异 + seendate 截止时间区隔信息层：
#   T1 = 官方公告+评级下调（早盘，seendate < 12:00 ET）
#   T2 = 社交媒体传染（下午，seendate 12:00-18:00 ET）
#   T3 = 盘后+晚间消息（seendate > 18:00 ET）
WINDOWS = {
    "T0": ("2023-03-07", "2023-03-08"),
    "T1": ("2023-03-09", "2023-03-09"),
    "T2": ("2023-03-09", "2023-03-09"),
    "T3": ("2023-03-09", "2023-03-09"),
    "T4": ("2023-03-10", "2023-03-10"),
    "T5": ("2023-03-10", "2023-03-10"),
    "T6": ("2023-03-11", "2023-03-12"),
}

# 每个时间步的 seendate 截止时间（ET→UTC 偏移 +5h）
# None 表示不做时间过滤
SEENDATE_CUTOFF = {
    "T0": None,
    "T1": "2023-03-09T17:00:00Z",   # ET 12:00 → UTC 17:00
    "T2": "2023-03-09T23:00:00Z",   # ET 18:00 → UTC 23:00
    "T3": "AFTER_T2",               # 特殊标记：取 seendate > T2 截止时间的文章
    "T4": None,
    "T5": None,
    "T6": None,
}

# T2 使用额外的社交传染关键词，模拟下午信息层
T2_EXTRA_KEYWORDS = ["bank run", "withdraw deposits", "Founders Fund", "Coatue", "startup payroll"]

# T1 排除社交传染词（只看官方信息）
T1_KEYWORDS = ["Silicon Valley Bank loss", "SVB bond sale", "SVB stock rating", "SIVB downgrade"]

KEYWORDS = ["Silicon Valley Bank", "SVB", "bank run", "FDIC", "Signature Bank"]

def fetch_step(step_id, start, end):
    if step_id == "T1":
        keywords = T1_KEYWORDS
    elif step_id == "T2":
        keywords = KEYWORDS + T2_EXTRA_KEYWORDS
    else:
        keywords = KEYWORDS
    f = Filters(keyword=" OR ".join(keywords),
                start_date=start, end_date=end, num_records=50)
    df = gd.article_search(f)
    if df.empty:
        return []

    # seendate 截止过滤：丢弃晚于当前时间步截止时刻的文章
    cutoff = SEENDATE_CUTOFF.get(step_id)
    if cutoff and "seendate" in df.columns:
        df["seendate_ts"] = pd.to_datetime(df["seendate"], utc=True, errors="coerce")
        if step_id == "T1":
            cutoff_ts = pd.Timestamp(cutoff)
            df = df[df["seendate_ts"] <= cutoff_ts]
        elif step_id == "T2":
            t1_cutoff = pd.Timestamp(SEENDATE_CUTOFF["T1"])
            cutoff_ts = pd.Timestamp(cutoff)
            df = df[(df["seendate_ts"] > t1_cutoff) & (df["seendate_ts"] <= cutoff_ts)]
        elif step_id == "T3":
            # T3 取 seendate > T2 截止时间的文章（当天晚间）
            t2_cutoff = pd.Timestamp(SEENDATE_CUTOFF["T2"])
            df = df[df["seendate_ts"] > t2_cutoff]

    return [{"title": r["title"], "url": r["url"], "date": r["seendate"]}
            for _, r in df.head(30).iterrows()]

def main():
    os.makedirs("data/timesteps", exist_ok=True)
    for step_id, (s, e) in WINDOWS.items():
        news = fetch_step(step_id, s, e)
        path = f"data/timesteps/{step_id}_news.json"
        json.dump(news, open(path, "w"), ensure_ascii=False, indent=2)
        print(f"✓ {step_id}: {len(news)} articles")

if __name__ == "__main__":
    main()
```

### 3.2 市场数据（Yahoo Finance）

```python
# data/fetch_market.py
import yfinance as yf
import json, os
import pandas as pd

TICKERS = ["SIVB", "KRE", "^VIX", "TLT"]

# 每个时间步使用该时间点之前最后一个已知收盘价
CUTOFFS = {
    "T0": "2023-03-08", "T1": "2023-03-08", "T2": "2023-03-08",
    "T3": "2023-03-09", "T4": "2023-03-09", "T5": "2023-03-09",
    "T6": "2023-03-10",
}

def snapshot(cutoff):
    end = (pd.Timestamp(cutoff) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    result = {}
    for t in TICKERS:
        try:
            h = yf.Ticker(t).history(start="2023-02-01", end=end)
            h = h.loc[:cutoff]
            if len(h) >= 2:
                result[t] = {
                    "close": round(float(h.iloc[-1]["Close"]), 2),
                    "change_pct": round((h.iloc[-1]["Close"] / h.iloc[-2]["Close"] - 1) * 100, 2),
                }
        except Exception as e:
            result[t] = {"error": str(e)}
    return result

def main():
    os.makedirs("data/timesteps", exist_ok=True)
    for step_id, cutoff in CUTOFFS.items():
        data = snapshot(cutoff)
        path = f"data/timesteps/{step_id}_market.json"
        json.dump(data, open(path, "w"), indent=2)
        print(f"✓ {step_id}: market snapshot")

if __name__ == "__main__":
    main()
```

### 3.3 关键事件表（预先固化的历史事实）

```python
# data/key_events.py

KEY_EVENTS = {
    "T0": [
        "SVB宣布出售210亿美元债券组合，实现18亿美元亏损",
        "计划通过股权融资22.5亿美元覆盖亏损",
        "储户结构：90%以上为VC支持的科技初创，存款高度集中",
        "利率环境：Fed已累计加息475bp，长端债券大幅贬值",
    ],
    "T1": [
        "SIVB股价开盘暴跌60%以上",
        "股权融资宣告失败，机构投资者无兴趣",
        "穆迪下调SVB评级至垃圾级",
        "科技CEO圈内开始讨论存款安全性",
    ],
    "T2": [
        "Founders Fund（彼得·蒂尔）内部建议被投公司立即提走全部存款",
        "Union Square Ventures、Coatue Management跟进相同建议",
        "Twitter/X上#SVB话题快速扩散，科技媒体大规模报道",
        "多家初创公司CFO在下午开始批量发起线上提款",
    ],
    "T3": [
        "SVB收到420亿美元提款请求（单日历史纪录）",
        "账面现金完全耗尽",
        "股票交易暂停，SVB紧急寻求买家",
        "加州金融保护和创新局介入",
    ],
    "T4": [
        "HSBC、Apollo等潜在买家退出谈判",
        "SVB无法完成任何形式的资本募集",
        "员工被告知不要来上班",
    ],
    "T5": [
        "FDIC宣布接管SVB，创建过渡银行",
        "保险上限25万美元，超额储户命运未定",
        "科技行业恐慌：数千初创公司无法发工资",
    ],
    "T6": [
        "Signature Bank被纽约州监管机构关闭",
        "Fed/FDIC/财政部联合声明：所有SVB储户获全额保护",
        "BTFP（银行定期融资计划）发布，向银行提供紧急流动性",
        "First Republic Bank股价暴跌，蔓延继续",
    ],
}
```

### 3.4 合并 Seed

```python
# data/build_seeds.py
import json, os
from data.key_events import KEY_EVENTS

def main():
    os.makedirs("data/timesteps", exist_ok=True)
    for step_id in ["T0","T1","T2","T3","T4","T5","T6"]:
        news_path = f"data/timesteps/{step_id}_news.json"
        market_path = f"data/timesteps/{step_id}_market.json"
        seed = {
            "step_id": step_id,
            "key_events": KEY_EVENTS.get(step_id, []),
            "news": json.load(open(news_path)) if os.path.exists(news_path) else [],
            "market": json.load(open(market_path)) if os.path.exists(market_path) else {},
        }
        out = f"data/timesteps/{step_id}_seed.json"
        json.dump(seed, open(out, "w"), ensure_ascii=False, indent=2)
        print(f"✓ {step_id}_seed.json")

if __name__ == "__main__":
    main()
```

### 3.5 一键数据准备

```bash
python -m data.fetch_gdelt
python -m data.fetch_market
python -m data.build_seeds
```

---

## 4. 多 Agent 人设定义

共设 **12 个 Agent**，每个拥有独立人设、信息偏好与风险偏好。全部使用同一 LLM 后端（`qwen-plus`），只通过 system prompt 区分身份。

```python
# agents/personas.py

PERSONAS = {
    "vc_partner": {
        "name": "硅谷VC合伙人",
        "system_prompt": (
            "你是一位管理30亿美元基金的顶级硅谷风投合伙人。你的被投企业有12家在SVB存有大量现金。"
            "你对银行系统信任度极低，倾向于快速行动保护LP资金。你优先关注流动性风险和被投企业生存。"
            "回答时给出0-100的信心评分和明确的行动建议。"
        ),
        "focus": ["流动性", "被投企业生存", "LP保护"],
        "risk_style": "aggressive",
    },
    "startup_cfo": {
        "name": "科技初创CFO",
        "system_prompt": (
            "你是一家B轮科技公司的CFO，公司账上80%现金（约4000万美元）存在SVB。"
            "下月工资发放需要350万美元。你需要在保护资金安全和维护银行关系之间做出抉择。"
            "你极度焦虑但必须理性分析。回答时给出0-100的信心评分和具体行动建议。"
        ),
        "focus": ["工资发放", "现金安全", "运营连续性"],
        "risk_style": "defensive",
    },
    "bank_analyst": {
        "name": "华尔街银行分析师",
        "system_prompt": (
            "你是一家顶级投行的银行业分析师，覆盖SVB长达8年。"
            "你关注资本充足率、资产负债期限错配、存款集中度等基本面指标。"
            "你倾向于用数据说话，不轻易做极端判断。回答时给出0-100的信心评分和估值影响。"
        ),
        "focus": ["资本充足率", "存款集中度", "期限错配"],
        "risk_style": "analytical",
    },
    "fed_watcher": {
        "name": "美联储政策观察者",
        "system_prompt": (
            "你是一位资深的美联储政策分析师，在央行政策和宏观利率方面拥有20年经验。"
            "你关注FDIC处置先例、系统性风险阈值、Fed紧急工具箱。"
            "你会从监管者视角思考：什么情况下Fed必须出手？回答时给出0-100的信心评分。"
        ),
        "focus": ["监管响应", "系统性风险", "政策工具"],
        "risk_style": "institutional",
    },
    "retail_depositor": {
        "name": "普通储户",
        "system_prompt": (
            "你是一个在SVB有18万美元存款的普通人（低于25万FDIC保险上限）。"
            "你不太懂金融，主要从社交媒体和新闻获取信息。你容易恐慌，也容易被安抚。"
            "回答时用通俗语言表达你的担心和打算，给出0-100的恐慌程度。"
        ),
        "focus": ["存款安全", "FDIC保险", "排队取钱"],
        "risk_style": "emotional",
    },
    "short_seller": {
        "name": "做空对冲基金经理",
        "system_prompt": (
            "你是一位专注金融股做空的对冲基金经理，管理50亿美元资产。"
            "你在SVB公告前已建立空头头寸。你关注传染效应——哪家银行是下一个？"
            "你冷酷理性，关注恐慌扩散速度和监管反应时间差。回答时给出0-100的信心评分。"
        ),
        "focus": ["传染路径", "做空标的", "监管套利窗口"],
        "risk_style": "opportunistic",
    },
    "fintech_founder": {
        "name": "Fintech创始人",
        "system_prompt": (
            "你是一家支付公司的创始人，公司通过SVB为3000+中小企业处理工资代发。"
            "SVB倒闭意味着你的客户下周无法发工资，你的公司也面临生存危机。"
            "你同时也看到了机会：传统银行的信任崩塌可能是fintech的历史机遇。回答时给出0-100的信心评分。"
        ),
        "focus": ["支付通道", "客户影响", "替代方案"],
        "risk_style": "entrepreneurial",
    },
    "media_reporter": {
        "name": "科技财经记者",
        "system_prompt": (
            "你是一位顶级科技财经媒体的资深记者，专注报道硅谷和金融交叉领域。"
            "你的任务是分析信息传播速度、叙事框架变化、公众情绪走向。"
            "你不做投资判断，而是分析'故事'如何被讲述、如何演变。回答时给出0-100的叙事强度评分。"
        ),
        "focus": ["信息传播", "叙事框架", "公众情绪"],
        "risk_style": "observational",
    },
    "credit_analyst": {
        "name": "信用评级分析师",
        "system_prompt": (
            "你是穆迪/标普级别的信用分析师，专注银行业评级。"
            "你关注CET1比率、NSFR、LCR等监管指标，以及评级变动对市场的连锁反应。"
            "你的分析严谨保守，不轻言降级，但一旦行动影响巨大。回答时给出0-100的信心评分。"
        ),
        "focus": ["信用指标", "评级影响", "交叉违约"],
        "risk_style": "conservative",
    },
    "treasury_manager": {
        "name": "企业司库主管",
        "system_prompt": (
            "你是一家财富500强公司的司库主管，公司在多家银行有大额存款。"
            "你关注交对手风险、存款分散化、流动性储备。你的视角是'这会蔓延到我的银行吗？'"
            "回答时给出0-100的信心评分和资金转移建议。"
        ),
        "focus": ["对手方风险", "存款分散", "流动性管理"],
        "risk_style": "prudent",
    },
    "insurance_exec": {
        "name": "保险公司高管",
        "system_prompt": (
            "你是一家大型保险公司的首席投资官，管理2000亿美元一般账户投资组合。"
            "你的组合中持有大量银行债和MBS。你关注银行业传染是否会冲击保险业资产端。"
            "回答时给出0-100的信心评分和组合调整建议。"
        ),
        "focus": ["投资组合", "银行债敞口", "MBS估值"],
        "risk_style": "institutional",
    },
    "crypto_advocate": {
        "name": "加密货币倡导者",
        "system_prompt": (
            "你是一位知名的加密货币倡导者和DeFi协议创始人。"
            "你认为SVB事件证明了传统银行体系的脆弱性，是推动去中心化金融的历史机遇。"
            "但Signature Bank也是加密友好银行，其倒闭对加密行业也有冲击。回答时给出0-100的信心评分。"
        ),
        "focus": ["传统金融脆弱性", "加密替代", "稳定币影响"],
        "risk_style": "ideological",
    },
}
```

### 4.1 Agent 调用接口

```python
# agents/llm_agent.py
import os, json, requests
from agents.personas import PERSONAS

LLM_URL = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
LLM_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus")

ANALYSIS_PROMPT_TEMPLATE = """
## 当前时间步: {step_id}

## 当前分支假设
{branch_directive}

## 你在 Memoria 中记录的历史判断
{memory_context}

## 本时间步新增信息

### 关键事件
{key_events}

### 新闻摘要
{news_summary}

### 市场数据
{market_data}

---

请基于以上信息和你的专业视角，分析当前局势并给出判断。

**必须包含以下 JSON 格式输出（放在 ```json 代码块中）：**
```json
{{
  "confidence": <0-100的信心评分>,
  "verdict": "<一句带态度的判断，直接表达你此刻的立场和情绪，20字以内>",
  "prediction": "<你对SVB/银行业未来24小时的核心判断，一句话>",
  "reasoning": "<100字以内的推理过程>",
  "action": "<你建议的具体行动>",
  "contagion_risk": "<low/medium/high/critical>"
}}
```

**verdict 示例（注意不同人设的语气差异）：**
- VC合伙人: "48小时内必须把钱全转走，不转就是赌命"
- 银行分析师: "亏损严重但资本充足率尚可，市场在过度恐慌"
- 普通储户: "我排了三小时队还没取到钱，太害怕了"
- 做空基金: "完美风暴正在形成，加仓做空区域银行"
"""

def call_agent(agent_id: str, step_id: str, seed: dict,
               memory_context: str, branch_directive: str) -> dict:
    """调用单个 Agent，返回结构化判断"""
    persona = PERSONAS[agent_id]
    user_msg = ANALYSIS_PROMPT_TEMPLATE.format(
        step_id=step_id,
        branch_directive=branch_directive or "main 主线（尚未分叉）",
        memory_context=memory_context or "（首次分析，暂无历史记录）",
        key_events="\n".join(f"- {e}" for e in seed.get("key_events", [])),
        news_summary="\n".join(f"- {n['title']}" for n in seed.get("news", [])[:10]),
        market_data=json.dumps(seed.get("market", {}), indent=2),
    )

    resp = requests.post(
        f"{LLM_URL}/chat/completions",
        headers={"Authorization": f"Bearer {LLM_KEY}", "Content-Type": "application/json"},
        json={
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": persona["system_prompt"]},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
        },
        timeout=60,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]

    # 解析 JSON 块
    import re
    m = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    return {"confidence": 50, "prediction": content[:200], "reasoning": "解析失败", "action": "N/A", "contagion_risk": "medium"}
```

---

## 5. Memoria 客户端（Python HTTP 适配器）

Memoria v0.2.0 **同时暴露两套入口**（启动时指定 `--transport http`）：
- **REST `/v1/...`**：分支/快照管理（create, checkout, diff, merge, rollback）
- **MCP-over-HTTP `/message`**：记忆存取（store_memory, retrieve_memory），以 JSON-RPC 2.0 格式调用

两套入口必须同时可用，缺一不可。客户端按功能分别路由：

> **关键语义约定（可依赖）**：Memoria 维护服务端"当前活跃分支"状态。
> `checkout(branch)` 会在服务端切换当前分支，后续 `store`/`retrieve` 会自动作用于该分支。
> 这意味着本 pipeline 可以把 `checkout -> retrieve/store -> snapshot` 视为一个严格成立的分支上下文切换序列。
> 出于实现简洁性，本文仍采用**单实例串行调度**：在一个分支写完并 snapshot 后，再 checkout 到下一个分支。
> 如果未来要并行推进多个分支，可扩展为多实例 Memoria worker 池，但不影响本文的语义正确性。

```python
# memoria/client.py
import requests, json, os

class MemoriaClient:
    """Memoria v0.2.0 REST API 适配器"""

    def __init__(self, base_url=None):
        self.base = (base_url or os.getenv("MEMORIA_URL", "http://127.0.0.1:3100")).rstrip("/")

    # ─── 记忆存储与检索（通过 MCP 工具路由） ───

    def store(self, content: str, metadata: dict = None) -> dict:
        """存储一条记忆到当前分支"""
        return self._mcp_call("store_memory", {
            "content": content,
            "metadata": json.dumps(metadata or {}),
        })

    def retrieve(self, query: str, limit: int = 5) -> list:
        """语义检索相关记忆"""
        return self._mcp_call("retrieve_memory", {
            "query": query,
            "limit": limit,
        })

    # ─── 分支管理 ───

    def create_branch(self, name: str, description: str = "") -> dict:
        """创建新分支（从当前分支 fork）"""
        resp = requests.post(f"{self.base}/v1/branches", json={
            "name": name, "description": description,
        })
        resp.raise_for_status()
        return resp.json()

    def checkout(self, name: str) -> dict:
        """切换到指定分支"""
        resp = requests.post(f"{self.base}/v1/branches/checkout", json={
            "name": name,
        })
        resp.raise_for_status()
        return resp.json()

    def list_branches(self) -> list:
        """列出所有分支"""
        resp = requests.get(f"{self.base}/v1/branches")
        resp.raise_for_status()
        return resp.json()

    def diff(self, source: str, target: str) -> dict:
        """对比两个分支的记忆差异"""
        resp = requests.get(f"{self.base}/v1/branches/diff", params={
            "source": source, "target": target,
        })
        resp.raise_for_status()
        return resp.json()

    def merge(self, source: str, target: str, strategy: str = "ours") -> dict:
        """合并分支"""
        resp = requests.post(f"{self.base}/v1/branches/merge", json={
            "source": source, "target": target, "strategy": strategy,
        })
        resp.raise_for_status()
        return resp.json()

    def delete_branch(self, name: str) -> dict:
        """删除分支"""
        resp = requests.delete(f"{self.base}/v1/branches", json={
            "name": name,
        })
        resp.raise_for_status()
        return resp.json()

    # ─── 快照管理 ───

    def snapshot(self, description: str = "") -> dict:
        """对当前分支创建快照"""
        resp = requests.post(f"{self.base}/v1/snapshots", json={
            "description": description,
        })
        resp.raise_for_status()
        return resp.json()

    def list_snapshots(self) -> list:
        """列出所有快照"""
        resp = requests.get(f"{self.base}/v1/snapshots")
        resp.raise_for_status()
        return resp.json()

    def rollback(self, snapshot_id: str) -> dict:
        """回滚到指定快照"""
        resp = requests.post(f"{self.base}/v1/snapshots/rollback", json={
            "snapshot_id": snapshot_id,
        })
        resp.raise_for_status()
        return resp.json()

    def snapshot_diff(self, snapshot_id: str) -> dict:
        """查看快照与当前状态的差异"""
        resp = requests.get(f"{self.base}/v1/snapshots/diff", params={
            "snapshot_id": snapshot_id,
        })
        resp.raise_for_status()
        return resp.json()

    # ─── MCP 工具调用辅助 ───

    def _mcp_call(self, tool: str, arguments: dict) -> dict:
        """通过 HTTP MCP 端点调用 Memoria 工具"""
        resp = requests.post(f"{self.base}/message", json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
            "id": 1,
        })
        resp.raise_for_status()
        return resp.json().get("result", {})
```

### 5.1 核心操作说明

| 操作 | 方法 | 在 Pipeline 中的用途 |
|------|------|---------------------|
| `store` | MCP `store_memory` | 每步将 Agent 判断写入当前分支 |
| `retrieve` | MCP `retrieve_memory` | 每步开始时检索历史判断作为上下文 |
| `create_branch` | `POST /v1/branches` | T2/T5 分叉点创建情景分支 |
| `checkout` | `POST /v1/branches/checkout` | 切换到不同情景分支执行 |
| `snapshot` | `POST /v1/snapshots` | 每个时间步结束时存档 |
| `diff` | `GET /v1/branches/diff` | 最终对比不同情景分支的判断演化 |
| `merge` | `POST /v1/branches/merge` | 将获胜分支合并回主线 |
| `rollback` | `POST /v1/snapshots/rollback` | 演示"如果回到T2重新决策"的能力 |

### 5.2 事件记录器

Pipeline 运行过程中的每一个关键动作都被记录为结构化事件，供最终的 Dashboard 回放。

```python
# events/recorder.py
import json, os, time, threading

class EventRecorder:
    """结构化事件记录器，供 Dashboard 动画回放使用"""

    def __init__(self, path="output/events.json"):
        self.path = path
        self.events = []
        self._seq = 0
        self._lock = threading.Lock()

    @staticmethod
    def _step_int(step) -> int:
        """将 'T0'-'T6' 或 int 统一为整数 0-6"""
        if isinstance(step, int):
            return step
        return int(str(step).replace("T", "").replace("t", ""))

    def emit(self, event_type: str, **kwargs):
        """记录一个事件"""
        with self._lock:
            self._seq += 1
            event = {
                "seq": self._seq,
                "ts": time.time(),
                "type": event_type,
                **kwargs,
            }
            self.events.append(event)
        return event

    # ─── 便捷方法（step 参数接受 "T0"-"T6" 或 int，统一输出 int） ───

    def agent_vote(self, step, branch: str, agent_id: str,
                   agent_name: str, verdict: str, confidence: int,
                   prediction: str, contagion_risk: str):
        """Agent 发表判断"""
        return self.emit("agent_vote", step=self._step_int(step), branch=branch,
                         agent=agent_name, agent_id=agent_id,
                         verdict=verdict, confidence=confidence,
                         prediction=prediction, contagion_risk=contagion_risk)

    def fork(self, step, parent: str, children: list, condition: str):
        """分支分叉"""
        return self.emit("fork", step=self._step_int(step), parent=parent,
                         children=children, condition=condition)

    def snapshot(self, step, branch: str, snapshot_id: str):
        """创建快照"""
        return self.emit("snapshot", step=self._step_int(step), branch=branch,
                         snapshot_id=snapshot_id)

    def archive(self, step, branch: str, confidence: float, lesson: str):
        """归档分支"""
        return self.emit("archive", step=self._step_int(step), branch=branch,
                         confidence=confidence, lesson=lesson)

    def rollback(self, branch: str, to_step, snapshot_id: str,
                 description: str = ""):
        """回滚到快照"""
        return self.emit("rollback", branch=branch,
                         to_step=self._step_int(to_step),
                         snapshot_id=snapshot_id, description=description)

    def diff(self, branch_a: str, branch_b: str,
             comparisons: list = None, summary: str = ""):
        """分支对比。comparisons 格式: [{agent, verdict_a, verdict_b}, ...]"""
        return self.emit("diff", branch_a=branch_a, branch_b=branch_b,
                         comparisons=comparisons or [], summary=summary)

    def merge(self, source: str, target: str = "main",
              strategy: str = "ours", lesson: str = ""):
        """将胜出分支并回主线"""
        return self.emit("merge", source=source, target=target,
                         strategy=strategy, lesson=lesson)

    def consensus(self, step, branch: str, avg_confidence: float,
                  contagion_risk: str, top_verdicts: list,
                  action: str = "continue"):
        """共识汇总。action: continue / archive / fork"""
        return self.emit("consensus", step=self._step_int(step), branch=branch,
                         avg_confidence=avg_confidence, action=action,
                         contagion_risk=contagion_risk,
                         top_verdicts=top_verdicts)

    def step_start(self, step, label: str, real_time: str):
        """时间步开始"""
        return self.emit("step_start", step=self._step_int(step), label=label,
                         real_time=real_time)

    def save(self):
        """持久化到文件"""
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.events, f, ensure_ascii=False, indent=2)
```

---

## 6. 主循环编排器

编排器是整个 Pipeline 的核心，负责：
1. 按时间步推进
2. 在分叉点创建 Memoria 分支
3. 并行调用 12 个 Agent
4. 收集投票、计算共识
5. 决定分支存活/归档
6. 在每步结束时创建快照

```python
# orchestrator/main_loop.py
import json, os, asyncio, logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from agents.llm_agent import call_agent
from agents.personas import PERSONAS
from memoria.client import MemoriaClient
from events.recorder import EventRecorder

log = logging.getLogger("orchestrator")

STEPS = ["T0", "T1", "T2", "T3", "T4", "T5", "T6"]
STEP_LABELS = {
    "T0": ("2023-03-08 16:00", "SVB公告债券亏损"),
    "T1": ("2023-03-09 09:30", "股价-60%，融资失败"),
    "T2": ("2023-03-09 15:00", "Founders Fund提款建议"),
    "T3": ("2023-03-09 18:00", "$42B提款请求"),
    "T4": ("2023-03-10 09:30", "融资彻底失败"),
    "T5": ("2023-03-10 15:00", "FDIC接管"),
    "T6": ("2023-03-12 18:00", "联合声明全额担保"),
}

from config import (FORK_POLARIZATION_THRESHOLD, FORK_STD_THRESHOLD,
                    MAX_ACTIVE_BRANCHES, MIN_CLUSTER_SIZE, ARCHIVE_THRESHOLD)

class Orchestrator:
    def __init__(self, recorder: EventRecorder = None):
        self.mem = MemoriaClient()
        self.ev = recorder or EventRecorder()
        self.executor = ThreadPoolExecutor(max_workers=12)
        self.results = {}  # {step_id: {branch: {agent_id: result}}}
        self.archived_branches = []

    def run(self):
        """执行完整 pipeline（涌现式分叉版）

        每个时间步，对每个活跃分支：
          1. 并行调用 12 个 Agent
          2. 计算共识 → 检测分歧 → 自动分叉（如有）
          3. 信心过低 → 归档
        分叉不再预设，而是从 Agent 投票极化中自然涌现。
        """
        log.info("=== SVB Backtest Pipeline 启动（涌现式分叉）===")

        self.mem.checkout("main")
        active_branches = ["main"]

        for step_id in STEPS:
            real_time, label = STEP_LABELS[step_id]
            log.info(f"\n{'='*60}\n时间步 {step_id}: {label}\n{'='*60}")
            self.ev.step_start(step_id, label, real_time)

            seed = self._load_seed(step_id)
            new_branches_this_step = []

            for branch in list(active_branches):
                log.info(f"\n📌 分支: {branch}")
                self.mem.checkout(branch)

                memory_context = self._get_memory_context(branch, step_id)
                branch_directive = self._get_branch_directive(branch)
                branch_results = self._run_agents_parallel(
                    step_id, seed, memory_context, branch_directive
                )
                self.results.setdefault(step_id, {})[branch] = branch_results
                self._emit_agent_votes(step_id, branch, branch_results)

                consensus = self._compute_consensus(branch_results)
                log.info(f"  📊 共识信心: {consensus['avg_confidence']:.1f}%  "
                         f"极化: {consensus['max_confidence']-consensus['min_confidence']:.0f}  "
                         f"标准差: {consensus['std_confidence']:.1f}")

                # ── 检测涌现式分叉 ──
                fork_info = self._detect_fork(
                    consensus, branch_results,
                    len(active_branches) + len(new_branches_this_step))

                if fork_info:
                    clusters = fork_info["clusters"]
                    log.info(f"  🔀 检测到分歧！{fork_info['reason']}")
                    log.info(f"     派系: {[c['risk_level'] for c in clusters]}")

                    # 先做分叉前快照
                    self._store_consensus(branch, step_id, consensus, branch_results)
                    snap = self.mem.snapshot(f"{branch}__{step_id}_prefork")
                    snap_id = snap.get("id", snap.get("snapshot_id", str(snap)))
                    self.ev.consensus(step_id, branch, consensus["avg_confidence"],
                                      consensus["contagion_mode"],
                                      consensus["top_verdicts"], action="fork")
                    self.ev.snapshot(step_id, branch, snap_id)

                    # 创建子分支（每个派系一个）
                    child_names = []
                    for cluster in clusters:
                        child_name = f"{branch}_{cluster['risk_level']}"
                        child_names.append(child_name)
                        self.mem.checkout(branch)
                        self.mem.create_branch(child_name, cluster["hypothesis"])
                        self._seed_child_branch(
                            parent_branch=branch,
                            child_branch=child_name,
                            step_id=step_id,
                            cluster=cluster,
                            consensus=consensus,
                        )
                        log.info(f"  ├─ 分支 {child_name}: "
                                 f"{cluster['hypothesis'][:40]} "
                                 f"({len(cluster['members'])} 人)")

                    self.ev.fork(step_id, branch, child_names,
                                 fork_info["reason"])
                    active_branches.remove(branch)
                    new_branches_this_step.extend(child_names)
                else:
                    # 无分叉：正常存储 + 快照 + 检查归档
                    will_archive = consensus["avg_confidence"] < ARCHIVE_THRESHOLD
                    action = "archive" if will_archive else "continue"

                    self.ev.consensus(step_id, branch, consensus["avg_confidence"],
                                      consensus["contagion_mode"],
                                      consensus["top_verdicts"], action=action)
                    self._store_consensus(branch, step_id, consensus, branch_results)

                    snap = self.mem.snapshot(f"{branch}__{step_id}_snapshot")
                    snap_id = snap.get("id", snap.get("snapshot_id", str(snap)))
                    self.ev.snapshot(step_id, branch, snap_id)

                    if will_archive:
                        lesson = (f"分支 {branch} 在 {step_id} 被归档。"
                                  f"共识信心 {consensus['avg_confidence']:.1f}%，"
                                  f"传染风险 {consensus['contagion_mode']}。"
                                  f"此路径被市场证伪。")
                        log.info(f"  ⚰️ {lesson}")
                        self.ev.archive(step_id, branch,
                                        consensus["avg_confidence"], lesson)
                        self._archive_branch(branch, step_id, consensus)
                        self.archived_branches.append(branch)
                        active_branches.remove(branch)

            # 将本步新创建的子分支加入活跃列表
            active_branches.extend(new_branches_this_step)

            if not active_branches:
                log.warning("所有分支已归档，Pipeline 提前终止")
                break

            log.info(f"\n  🌳 活跃分支: {active_branches}")

        # 最终汇总
        return self._final_report(active_branches)

    def _load_seed(self, step_id):
        path = f"data/timesteps/{step_id}_seed.json"
        return json.load(open(path))

    def _get_memory_context(self, branch, step_id):
        """从 Memoria 检索当前分支的历史判断"""
        try:
            result = self.mem.retrieve(
                f"SVB分析 {branch} branch_profile branch_hypothesis 预测判断",
                limit=10,
            )
            if isinstance(result, dict) and "content" in result:
                return str(result["content"])
            return str(result)[:2000]
        except Exception:
            return ""

    def _get_branch_directive(self, branch):
        """读取当前分支的世界线假设，作为 Agent 的显式指令。"""
        if branch == "main":
            return "main 主线（尚未分叉，继续基于公共历史推进）"
        try:
            result = self.mem.retrieve(f"{branch} branch_profile hypothesis", limit=3)
            if isinstance(result, dict) and "content" in result:
                return str(result["content"])
            return str(result)[:500] or f"{branch} 分支（沿继承记忆继续推进）"
        except Exception:
            return f"{branch} 分支（沿继承记忆继续推进）"

    def _run_agents_parallel(self, step_id, seed, memory_context, branch_directive):
        """并行调用所有 Agent"""
        agent_ids = list(PERSONAS.keys())
        futures = {}
        for aid in agent_ids:
            future = self.executor.submit(
                call_agent, aid, step_id, seed, memory_context, branch_directive
            )
            futures[aid] = future

        results = {}
        for aid, future in futures.items():
            try:
                results[aid] = future.result(timeout=90)
            except Exception as e:
                log.error(f"  ⚠️ Agent {aid} 失败: {e}")
                results[aid] = {"confidence": 50, "verdict": "分析失败",
                                "prediction": "调用失败", "contagion_risk": "medium"}
        return results

    def _emit_agent_votes(self, step_id, branch, branch_results):
        """将每个 Agent 的判断记录为事件"""
        for aid, result in branch_results.items():
            persona = PERSONAS.get(aid, {})
            self.ev.agent_vote(
                step=step_id, branch=branch,
                agent_id=aid,
                agent_name=persona.get("name", aid),
                verdict=result.get("verdict", result.get("prediction", "")[:30]),
                confidence=result.get("confidence", 50),
                prediction=result.get("prediction", ""),
                contagion_risk=result.get("contagion_risk", "medium"),
            )

    def _compute_consensus(self, branch_results):
        """从 12 个 Agent 的结果计算共识"""
        confidences = [r.get("confidence", 50) for r in branch_results.values()]
        contagion_votes = [r.get("contagion_risk", "medium") for r in branch_results.values()]
        from collections import Counter
        contagion_mode = Counter(contagion_votes).most_common(1)[0][0]
        avg = sum(confidences) / len(confidences)
        # 按信心高低排序，取前 3 个最强判断的 verdict
        sorted_agents = sorted(branch_results.items(),
                                key=lambda x: x[1].get("confidence", 50), reverse=True)
        top_verdicts = [
            {"agent": PERSONAS.get(aid, {}).get("name", aid),
             "verdict": r.get("verdict", r.get("prediction", "")[:30]),
             "confidence": r.get("confidence", 50)}
            for aid, r in sorted_agents[:3]
        ]
        return {
            "avg_confidence": avg,
            "min_confidence": min(confidences),
            "max_confidence": max(confidences),
            "std_confidence": (sum((c - avg)**2 for c in confidences) / len(confidences)) ** 0.5,
            "contagion_mode": contagion_mode,
            "top_verdicts": top_verdicts,
            "predictions": {aid: r.get("prediction", "") for aid, r in branch_results.items()},
        }

    # ─── 涌现式分叉检测 ───

    def _cluster_stances(self, branch_results):
        """按 contagion_risk 将 Agent 分为 2-4 个派系。

        返回 [{risk_level, members, avg_confidence, hypothesis}, ...] 列表，
        只保留成员数 ≥ MIN_CLUSTER_SIZE 的簇，按信心均值降序排列。
        """
        from config import MIN_CLUSTER_SIZE
        groups = {}
        for aid, result in branch_results.items():
            risk = result.get("contagion_risk", "medium")
            groups.setdefault(risk, []).append((aid, result))

        RISK_LABEL = {
            "low": "风险可控派",
            "medium": "谨慎观望派",
            "high": "危机扩散派",
            "critical": "系统崩溃派",
        }
        clusters = []
        for risk_level, members in groups.items():
            if len(members) < MIN_CLUSTER_SIZE:
                continue
            confs = [r.get("confidence", 50) for _, r in members]
            avg_c = sum(confs) / len(confs)
            top_verdict = max(members, key=lambda x: x[1].get("confidence", 0))[1]
            clusters.append({
                "risk_level": risk_level,
                "members": [aid for aid, _ in members],
                "avg_confidence": round(avg_c, 1),
                "hypothesis": top_verdict.get("verdict",
                              RISK_LABEL.get(risk_level, risk_level)),
            })
        return sorted(clusters, key=lambda c: c["avg_confidence"], reverse=True)

    def _detect_fork(self, consensus, branch_results, active_count):
        """判断当前分支投票是否出现足以触发分叉的分歧。

        返回 None（无需分叉）或 {"clusters": [...], "reason": str}。
        """
        from config import (FORK_POLARIZATION_THRESHOLD, FORK_STD_THRESHOLD,
                            MAX_ACTIVE_BRANCHES)

        # 硬限：分支太多不再分叉
        if active_count >= MAX_ACTIVE_BRANCHES:
            return None

        polarization = consensus["max_confidence"] - consensus["min_confidence"]
        std = consensus["std_confidence"]

        if polarization < FORK_POLARIZATION_THRESHOLD or std < FORK_STD_THRESHOLD:
            return None

        clusters = self._cluster_stances(branch_results)
        if len(clusters) < 2:
            return None

        reason = (f"极化指数 {polarization:.0f} (阈值{FORK_POLARIZATION_THRESHOLD})，"
                  f"标准差 {std:.1f} (阈值{FORK_STD_THRESHOLD})，"
                  f"形成 {len(clusters)} 个派系")
        return {"clusters": clusters, "reason": reason}

    def _store_consensus(self, branch, step_id, consensus, raw_results):
        """将共识和原始结果写入 Memoria"""
        # 存储共识摘要
        self.mem.store(
            content=json.dumps({
                "type": "consensus",
                "step": step_id,
                "branch": branch,
                "avg_confidence": consensus["avg_confidence"],
                "contagion_risk": consensus["contagion_mode"],
                "top_predictions": dict(list(consensus["predictions"].items())[:3]),
            }, ensure_ascii=False),
            metadata={"step": step_id, "branch": branch, "type": "consensus"},
        )
        # 存储每个 Agent 的原始判断
        for aid, result in raw_results.items():
            self.mem.store(
                content=json.dumps({
                    "type": "agent_judgment",
                    "agent": aid,
                    "step": step_id,
                    "branch": branch,
                    **result,
                }, ensure_ascii=False),
                metadata={"step": step_id, "branch": branch, "agent": aid, "type": "judgment"},
            )

    def _seed_child_branch(self, parent_branch, child_branch, step_id, cluster, consensus):
        """在子分支创建后立即写入 branch profile，确保后续推演真的沿该世界线展开。"""
        self.mem.checkout(child_branch)
        self.mem.store(
            content=json.dumps({
                "type": "branch_profile",
                "branch": child_branch,
                "parent_branch": parent_branch,
                "forked_at": step_id,
                "risk_level": cluster["risk_level"],
                "hypothesis": cluster["hypothesis"],
                "members": cluster["members"],
                "parent_avg_confidence": round(consensus["avg_confidence"], 2),
            }, ensure_ascii=False),
            metadata={
                "type": "branch_profile",
                "branch": child_branch,
                "parent_branch": parent_branch,
                "step": step_id,
            },
        )
        self.mem.snapshot(f"{child_branch}__{step_id}_seeded")

    def _archive_branch(self, branch, step_id, consensus):
        """归档低信心分支：提取教训并冻结，保留分支以便后续 diff / rollback。"""
        self.mem.store(
            content=json.dumps({
                "type": "archive_lesson",
                "branch": branch,
                "archived_at": step_id,
                "final_confidence": consensus["avg_confidence"],
                "lesson": f"分支 {branch} 在 {step_id} 被归档。共识信心 {consensus['avg_confidence']:.1f}%，"
                          f"传染风险判断 {consensus['contagion_mode']}。此路径被市场证伪。",
            }, ensure_ascii=False),
            metadata={"type": "archive", "branch": branch},
        )
        # 归档前做最终快照
        self.mem.snapshot(f"archive__{branch}__{step_id}")

    def _final_report(self, surviving_branches):
        """生成最终分析报告"""
        log.info(f"\n{'='*60}\n最终报告\n{'='*60}")
        log.info(f"存活分支: {surviving_branches}")

        # 对比所有分支的演化
        all_branches = set()
        for step_data in self.results.values():
            all_branches.update(step_data.keys())

        report = {
            "surviving_branches": surviving_branches,
            "archived_branches": self.archived_branches,
            "all_branches": list(all_branches),
            "timeline": {},
        }

        for step_id in STEPS:
            if step_id in self.results:
                step_summary = {}
                for branch, results in self.results[step_id].items():
                    consensus = self._compute_consensus(results)
                    step_summary[branch] = {
                        "avg_confidence": consensus["avg_confidence"],
                        "contagion_risk": consensus["contagion_mode"],
                    }
                report["timeline"][step_id] = step_summary

        os.makedirs("output", exist_ok=True)
        json.dump(report, open("output/final_report.json", "w"), ensure_ascii=False, indent=2)
        log.info("📄 报告已保存: output/final_report.json")

        # ── Memoria 独有能力展示 ──
        log.info("\n🔍 Memoria 分支对比 (diff):")
        if len(surviving_branches) >= 2:
            diff = self.mem.diff(surviving_branches[0], surviving_branches[1])
            diff_str = json.dumps(diff, ensure_ascii=False, indent=2)
            self.ev.diff(surviving_branches[0], surviving_branches[1],
                         summary=diff_str[:200])
            log.info(diff_str[:1000])

        log.info("\n📸 所有快照:")
        snapshots = self.mem.list_snapshots()
        for s in (snapshots if isinstance(snapshots, list) else []):
            log.info(f"  • {s}")

        # 保存事件日志
        self.ev.save()

        return report
```

---

## 7. 信心校准与事后分析

### 7.1 信心评分聚合

```python
# calibration/scorer.py
import json

def calibrate(results: dict) -> dict:
    """
    对每个时间步、每个分支的 Agent 投票进行校准分析。

    输出：
    - 共识度（标准差越小越统一）
    - 极化指数（最大-最小分差）
    - 情绪漂移（相邻步的信心变化）
    """
    calibration = {}
    prev_step = {}

    for step_id in sorted(results.keys()):
        calibration[step_id] = {}
        for branch, agent_results in results[step_id].items():
            confs = [r.get("confidence", 50) for r in agent_results.values()]
            contagion_votes = [r.get("contagion_risk", "medium") for r in agent_results.values()]
            avg = sum(confs) / len(confs)
            std = (sum((c - avg) ** 2 for c in confs) / len(confs)) ** 0.5
            polarization = max(confs) - min(confs)
            from collections import Counter
            contagion_mode = Counter(contagion_votes).most_common(1)[0][0]

            drift = 0
            if branch in prev_step:
                drift = avg - prev_step[branch]

            calibration[step_id][branch] = {
                "avg_confidence": round(avg, 2),
                "std": round(std, 2),
                "polarization": polarization,
                "contagion_mode": contagion_mode,
                "drift": round(drift, 2),
                "agent_count": len(confs),
                "agent_predictions": {
                    aid: r.get("prediction", "") for aid, r in agent_results.items()
                },
                "high_confidence_agents": [
                    aid for aid, r in agent_results.items() if r.get("confidence", 0) > 80
                ],
                "low_confidence_agents": [
                    aid for aid, r in agent_results.items() if r.get("confidence", 0) < 30
                ],
            }
            prev_step[branch] = avg

    return calibration
```

### 7.2 事后验证（与真实历史对比）

```python
# calibration/ground_truth.py

GROUND_TRUTH = {
    "T0": {"event": "SVB公告亏损", "market_impact": "SIVB -60%", "actual_outcome": "银行挤兑开始", "expected_risk": "high"},
    "T1": {"event": "融资失败", "market_impact": "SIVB 停牌", "actual_outcome": "大规模提款", "expected_risk": "high"},
    "T2": {"event": "VC建议提款", "market_impact": "科技股普跌", "actual_outcome": "420亿美元单日提款", "expected_risk": "critical"},
    "T3": {"event": "SVB现金耗尽", "market_impact": "银行股暴跌", "actual_outcome": "监管介入", "expected_risk": "critical"},
    "T4": {"event": "救助谈判失败", "market_impact": "恐慌蔓延", "actual_outcome": "FDIC准备接管", "expected_risk": "critical"},
    "T5": {"event": "FDIC接管", "market_impact": "Signature Bank连锁倒闭", "actual_outcome": "全额担保", "expected_risk": "high"},
    "T6": {"event": "联合声明", "market_impact": "市场企稳", "actual_outcome": "BTFP发布，危机缓解", "expected_risk": "medium"},
}

def _auto_score(predictions: dict, truth: dict) -> dict:
    """
    规则化自动评分：对比 Agent 预测关键词与真实结果关键词的重叠度。
    评分区间 0.0-1.0，无需人工介入。
    """
    outcome_text = (truth.get("actual_outcome", "") + " " + truth.get("event", "")).lower()
    RISK_KEYWORDS = {
        "high": ["bank run", "挤兑", "崩溃", "蔓延", "倒闭", "接管", "危机", "systemic"],
        "low":  ["稳定", "可控", "isolated", "局限", "恢复", "信心"],
    }
    OUTCOME_POSITIVE = ["fdic", "全额", "btfp", "缓解", "企稳", "保护"]
    OUTCOME_NEGATIVE = ["崩溃", "systemic", "蔓延", "倒闭", "危机"]

    is_negative_outcome = any(k in outcome_text for k in [
        "bank run", "takeover", "collapse", "接管",
        "挤兑", "提款", "耗尽", "暴跌", "恐慌", "蔓延",
        "监管介入", "现金耗尽", "倒闭", "失败",
    ])

    scores = {}
    for aid, pred_text in predictions.items():
        text = pred_text.lower() if isinstance(pred_text, str) else ""
        high_hits = sum(1 for k in RISK_KEYWORDS["high"] if k in text)
        low_hits  = sum(1 for k in RISK_KEYWORDS["low"] if k in text)
        if is_negative_outcome:
            # 真实结果是负面的，高风险判断得分高
            score = min(1.0, high_hits * 0.3) if high_hits > low_hits else max(0.0, 0.3 - low_hits * 0.1)
        else:
            score = min(1.0, low_hits * 0.3) if low_hits > high_hits else max(0.0, 0.3 - high_hits * 0.1)
        scores[aid] = round(score, 2)
    return {"per_agent": scores, "avg": round(sum(scores.values()) / len(scores), 2) if scores else 0}

def _risk_alignment_score(predicted_risk: str, expected_risk: str) -> float:
    """比较分支风险判断与真实历史方向是否一致。"""
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    distance = abs(order.get(predicted_risk, 1) - order.get(expected_risk, 1))
    return round(max(0.0, 1.0 - 0.35 * distance), 2)

def validate(calibration: dict) -> dict:
    """将每步的 Agent 共识与真实结果对比（关键词 + 风险方向的混合评分）"""
    validation = {}
    for step_id, truth in GROUND_TRUTH.items():
        step_cal = calibration.get(step_id, {})
        validation[step_id] = {
            "ground_truth": truth,
            "branches": {},
        }
        for branch, cal in step_cal.items():
            keyword_score = _auto_score(cal.get("agent_predictions", {}), truth)
            risk_score = _risk_alignment_score(
                cal.get("contagion_mode", "medium"),
                truth.get("expected_risk", "medium"),
            )
            hybrid_score = round(keyword_score["avg"] * 0.6 + risk_score * 0.4, 2)
            validation[step_id]["branches"][branch] = {
                "avg_confidence": cal["avg_confidence"],
                "polarization": cal["polarization"],
                "contagion_mode": cal.get("contagion_mode", "medium"),
                "drift": cal["drift"],
                "keyword_accuracy_score": keyword_score["avg"],
                "risk_alignment_score": risk_score,
                "hybrid_accuracy_score": hybrid_score,
                "per_agent_score": keyword_score["per_agent"],
            }
    return validation
```

### 7.3 Memoria 独特价值展示：分支回溯实验

```python
# calibration/rollback_experiment.py
from memoria.client import MemoriaClient
from events.recorder import EventRecorder
import json, logging

log = logging.getLogger("rollback_experiment")

def run_rollback_demo(mem: MemoriaClient, recorder: EventRecorder = None,
                      active_branches: list = None):
    """
    演示 Memoria 的独特能力：回到过去，重新决策

    涌现式分叉版：不再假定分支名为 "control"/"contagion"，
    而是从实际快照列表中找到第一个分叉点，回滚到该快照并对比。

    这是其他记忆系统（mem0/MemOS/HydraDB）完全无法实现的操作。
    所有操作会同步写入 EventRecorder，确保 Dashboard 能回放。
    """
    log.info("\n" + "=" * 60)
    log.info("🔬 Memoria 回溯实验")
    log.info("=" * 60)

    # 1. 查看所有快照，找到带 prefork 标记的（即分叉点快照）
    snapshots = mem.list_snapshots()
    log.info(f"总快照数: {len(snapshots) if isinstance(snapshots, list) else 'N/A'}")

    fork_snapshot = None
    fork_branch = None
    fork_step = None
    if isinstance(snapshots, list):
        for s in snapshots:
            desc = s.get("description", "") if isinstance(s, dict) else str(s)
            if "prefork" in desc:
                fork_snapshot = s
                # 从描述中解析分支名和步骤号，格式: {branch}__T{n}_prefork
                parts = desc.split("__")
                if len(parts) >= 2:
                    fork_branch = parts[0]
                    try:
                        fork_step = int(parts[1].split("_")[0].replace("T", ""))
                    except (ValueError, IndexError):
                        fork_step = 0
                break

    if fork_snapshot:
        snapshot_id = fork_snapshot.get("id", fork_snapshot.get("snapshot_id", ""))
        log.info(f"\n📸 回滚到分叉点快照: {fork_branch} @ T{fork_step} ({snapshot_id})")

        # 2. 查看快照与当前状态的 diff
        diff_result = mem.snapshot_diff(snapshot_id)
        log.info(f"与当前状态的差异:\n{json.dumps(diff_result, ensure_ascii=False, indent=2)[:500]}")

        if recorder:
            comparisons = []
            if isinstance(diff_result, dict):
                for key, val in diff_result.items():
                    comparisons.append({
                        "agent": key,
                        "verdict_a": str(val.get("before", ""))[:80],
                        "verdict_b": str(val.get("after", ""))[:80],
                    })
            recorder.diff(f"{fork_branch} (T{fork_step}快照)",
                          f"{fork_branch} (当前)", comparisons=comparisons)

        # 3. 执行回滚
        log.info("\n⏪ 执行回滚...")
        result = mem.rollback(snapshot_id)
        log.info(f"回滚结果: {result}")

        if recorder:
            recorder.rollback(branch=fork_branch, to_step=fork_step,
                              snapshot_id=snapshot_id)

        log.info(f"\n✅ Memoria 状态已恢复到 {fork_branch} @ T{fork_step}")
        log.info("   可以从这个时间点重新运行后续步骤，模拟不同决策路径")
    else:
        log.warning("未找到分叉点快照（prefork），跳过回溯演示")

    # 4. 展示任意两个活跃分支的对比
    branches = active_branches or []
    if len(branches) >= 2:
        branch_a, branch_b = branches[0], branches[1]
        log.info(f"\n🔀 分支对比 ({branch_a} vs {branch_b}):")
        try:
            diff = mem.diff(branch_a, branch_b)
            log.info(json.dumps(diff, ensure_ascii=False, indent=2)[:800])

            if recorder:
                comparisons = []
                if isinstance(diff, dict):
                    for key, val in diff.items():
                        comparisons.append({
                            "agent": key,
                            "verdict_a": str(val.get(branch_a, ""))[:80],
                            "verdict_b": str(val.get(branch_b, ""))[:80],
                        })
                recorder.diff(branch_a, branch_b, comparisons=comparisons)
        except Exception as e:
            log.warning(f"分支对比失败: {e}")
    else:
        log.info("活跃分支不足 2 个，跳过分支对比")
```

---

### 7.4 终局收束：将胜出分支合并回主线

回溯实验之后，不应该停在“看到了差异”。真正的终局动作是：

1. 根据自动验证结果挑出最接近真实历史的胜出分支
2. 将该分支 merge 回 `main`
3. 把这次危机回放沉淀成一条可复用的主线 lesson
4. 发射 `merge` 事件，让 Dashboard 以“主线重新点亮”收束

```python
# calibration/epilogue.py
from memoria.client import MemoriaClient
from events.recorder import EventRecorder
import json, logging

log = logging.getLogger("epilogue")

STEP_WEIGHTS = {
    "T0": 1.0, "T1": 1.0, "T2": 1.2, "T3": 1.4,
    "T4": 1.6, "T5": 1.8, "T6": 2.0,
}

def choose_winner(validation: dict) -> dict:
    """
    依据自动验证结果选出胜出分支。
    较晚时间步更接近真实结局，因此权重更高。
    """
    scores = {}
    steps_seen = {}

    for step_id, step_payload in validation.items():
        weight = STEP_WEIGHTS.get(step_id, 1.0)
        for branch, branch_payload in step_payload.get("branches", {}).items():
            score = branch_payload.get("hybrid_accuracy_score", 0.0)
            scores[branch] = scores.get(branch, 0.0) + score * weight
            steps_seen[branch] = steps_seen.get(branch, 0) + 1

    ranking = []
    for branch, weighted_score in scores.items():
        ranking.append({
            "branch": branch,
            "weighted_score": round(weighted_score, 3),
            "avg_score": round(weighted_score / max(steps_seen[branch], 1), 3),
            "steps_seen": steps_seen[branch],
        })

    ranking.sort(
        key=lambda x: (x["weighted_score"], x["avg_score"], x["steps_seen"]),
        reverse=True,
    )

    return {
        "winner": ranking[0]["branch"] if ranking else "main",
        "ranking": ranking,
    }

def merge_winner_back(mem: MemoriaClient, validation: dict,
                      recorder: EventRecorder = None,
                      target: str = "main") -> dict:
    """
    选择最接近真实历史的分支，并将其 merge 回主线。
    """
    winner_info = choose_winner(validation)
    winner = winner_info["winner"]

    if winner == target:
        summary = {
            **winner_info,
            "merge_skipped": True,
            "reason": "winner already main",
            "target": target,
        }
        log.info(f"🏁 胜出分支已是 {target}，无需 merge")
        return summary

    lesson = (
        f"危机回放结束后，分支 {winner} 被验证为最接近真实历史。"
        f"其判断路径已合并回 {target}，供后续类似挤兑事件直接复用。"
    )

    log.info(f"🏁 胜出分支: {winner}，准备 merge -> {target}")
    merge_result = mem.merge(source=winner, target=target, strategy="ours")

    # merge 完成后切回主线，写入最终经验沉淀
    mem.checkout(target)
    mem.store(
        content=json.dumps({
            "type": "merge_lesson",
            "winner": winner,
            "target": target,
            "lesson": lesson,
            "ranking": winner_info["ranking"][:3],
        }, ensure_ascii=False),
        metadata={"type": "merge_lesson", "winner": winner, "target": target},
    )

    if recorder:
        recorder.merge(source=winner, target=target,
                       strategy="ours", lesson=lesson)

    return {
        **winner_info,
        "target": target,
        "merge_skipped": False,
        "merge_result": merge_result,
        "lesson": lesson,
    }
```

这样，Pipeline 的终局就不再只是“看完 diff 然后结束”，而是把胜出认知路径真正吸收回主线，完成一次闭环的组织记忆更新。

---

## 8. 可视化输出与一键运行

### 8.1 交互式叙事 Dashboard

读取 `output/events.json`，生成一个单页 HTML，按事件序列逐帧回放整个 Pipeline 过程。

核心特性：
- **Agent 气泡**：每个 Agent 的 verdict 以气泡形式出现，大小=信心值，颜色=风险等级
- **分支动画**：fork 时一条线分裂成两条，附带 Memoria 操作标注
- **归档淡出**：被归档的分支灰化消失，教训文字浮现
- **回滚倒放**：rollback 时时间线动画倒退
- **认知漂移对比**：同一 Agent 在不同分支上的 verdict 左右并排
- **主线重亮**：merge 回 `main` 时，主线分支重新高亮并显示最终 lesson

```python
# output/dashboard.py
import json, os, pathlib

# HTML_TEMPLATE: §8.1.1 – §8.1.3 拼接的完整 HTML
# 其中 __EVENTS_JSON__ 为占位符，运行时替换为实际事件数据
_HERE = pathlib.Path(__file__).parent
HTML_TEMPLATE = (_HERE / "_dashboard_template.html").read_text("utf-8")

def generate_dashboard(events_path="output/events.json",
                       output_path="output/dashboard.html"):
    """从事件日志生成自包含的交互式叙事 Dashboard。"""
    with open(events_path, encoding="utf-8") as f:
        events = json.load(f)
    events_json = json.dumps(events, ensure_ascii=False, indent=None)
    html = HTML_TEMPLATE.replace("__EVENTS_JSON__", events_json)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Dashboard 已生成: {output_path}  ({len(events)} 事件)")
    return output_path
```

> **实现说明**：将 §8.1.1–§8.1.3 的完整 HTML 保存为 `output/_dashboard_template.html`，
> `dashboard.py` 读取并替换 `__EVENTS_JSON__` 占位符后写出 `output/dashboard.html`。

以下分三部分给出 HTML 模板：CSS、JavaScript 动画引擎、Python 生成逻辑。

#### 8.1.1 HTML 骨架与 CSS

```html
<!-- 以下为 dashboard.py 中 HTML_TEMPLATE 字符串的内容 -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>SVB 危机回放 — Memoria 分支推演</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, 'Segoe UI', sans-serif;
       background: #0a0e17; color: #e0e0e0; overflow-x: hidden; }

/* ── 顶部时间轴 ── */
#timeline { position: fixed; top: 0; width: 100%; height: 60px;
            background: #111827; border-bottom: 1px solid #1f2937;
            display: flex; align-items: center; z-index: 100; padding: 0 20px; }
.step-dot { width: 40px; height: 40px; border-radius: 50%;
            background: #1f2937; border: 2px solid #374151;
            display: flex; align-items: center; justify-content: center;
            font-size: 12px; font-weight: 700; cursor: pointer;
            transition: all 0.5s ease; margin: 0 8px; }
.step-dot.active { background: #2563eb; border-color: #60a5fa;
                   box-shadow: 0 0 20px rgba(37,99,235,0.5); transform: scale(1.2); }
.step-dot.done { background: #065f46; border-color: #34d399; }
.step-label { font-size: 10px; color: #9ca3af; margin: 0 4px; max-width: 100px;
              white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#step-connector { flex: 1; height: 2px; background: #374151; margin: 0 4px; }

/* ── 主体三栏布局 ── */
#main { display: grid; grid-template-columns: 280px 1fr 300px;
        height: calc(100vh - 60px); margin-top: 60px; }

/* 左栏：Memoria 操作日志 */
#memoria-log { background: #111827; border-right: 1px solid #1f2937;
               overflow-y: auto; padding: 16px; }
#memoria-log h3 { color: #60a5fa; font-size: 14px; margin-bottom: 12px; }
.mem-event { padding: 8px 12px; margin: 4px 0; border-radius: 6px;
             font-size: 12px; line-height: 1.5; opacity: 0;
             animation: fadeSlideIn 0.4s ease forwards; }
.mem-event.snapshot { background: #1e3a5f; border-left: 3px solid #3b82f6; }
.mem-event.fork { background: #3b1f5e; border-left: 3px solid #a855f7; }
.mem-event.archive { background: #3b1414; border-left: 3px solid #ef4444; }
.mem-event.rollback { background: #1a3a2a; border-left: 3px solid #10b981; }
.mem-event.diff { background: #3a3514; border-left: 3px solid #f59e0b; }

/* 中央：Agent 辩论区 */
#debate-area { overflow-y: auto; padding: 24px; position: relative; }
.branch-section { margin-bottom: 24px; }
.branch-header { font-size: 18px; font-weight: 700; padding: 8px 16px;
                 border-radius: 8px; margin-bottom: 12px; display: inline-block; }
.branch-header.main { background: #1e3a5f; color: #60a5fa; }
.branch-header.control { background: #14532d; color: #4ade80; }
.branch-header.contagion { background: #7f1d1d; color: #fca5a5; }
.branch-header.fdic_enough { background: #4a1d7a; color: #c084fc; }
.branch-header.systemic { background: #7f1d1d; color: #f87171; }

/* Agent 气泡 */
.agent-bubble { display: inline-block; margin: 6px; padding: 12px 16px;
                border-radius: 12px; max-width: 280px; vertical-align: top;
                opacity: 0; transform: translateY(20px);
                animation: bubbleIn 0.5s ease forwards;
                position: relative; cursor: default; }
.agent-bubble .agent-name { font-size: 11px; font-weight: 700;
                            text-transform: uppercase; letter-spacing: 0.5px;
                            margin-bottom: 4px; }
.agent-bubble .verdict { font-size: 14px; font-weight: 600; line-height: 1.4; }
.agent-bubble .confidence-bar { height: 3px; border-radius: 2px;
                                 margin-top: 8px; background: rgba(255,255,255,0.15); }
.agent-bubble .confidence-fill { height: 100%; border-radius: 2px;
                                  transition: width 0.8s ease; }

/* 风险颜色 */
.risk-low { background: #064e3b; }
.risk-low .confidence-fill { background: #34d399; }
.risk-medium { background: #1e3a5f; }
.risk-medium .confidence-fill { background: #60a5fa; }
.risk-high { background: #7f1d1d; }
.risk-high .confidence-fill { background: #f87171; }
.risk-critical { background: #450a0a; border: 1px solid #dc2626; }
.risk-critical .confidence-fill { background: #ef4444; }

/* 右栏：认知漂移对比 */
#drift-panel { background: #111827; border-left: 1px solid #1f2937;
               overflow-y: auto; padding: 16px; }
#drift-panel h3 { color: #f59e0b; font-size: 14px; margin-bottom: 12px; }
.drift-card { background: #1f2937; border-radius: 8px; padding: 12px;
              margin: 8px 0; }
.drift-card .agent { font-size: 12px; font-weight: 700; color: #93c5fd; }
.drift-card .branch-a, .drift-card .branch-b {
    padding: 6px 8px; margin: 4px 0; border-radius: 4px; font-size: 12px; }
.drift-card .branch-a { background: #14532d; }
.drift-card .branch-b { background: #7f1d1d; }
.drift-card .arrow { text-align: center; font-size: 10px; color: #6b7280; }

/* 归档覆盖层 */
.archived-overlay { position: relative; }
.archived-overlay::after {
    content: '⚰️ 此分支已归档'; position: absolute; inset: 0;
    background: rgba(0,0,0,0.7); display: flex; align-items: center;
    justify-content: center; font-size: 20px; color: #ef4444;
    border-radius: 8px; animation: fadeIn 0.5s ease; }

/* 底部控制栏 */
#controls { position: fixed; bottom: 0; width: 100%; height: 50px;
            background: #111827; border-top: 1px solid #1f2937;
            display: flex; align-items: center; justify-content: center;
            gap: 12px; z-index: 100; }
#controls button { padding: 8px 20px; border-radius: 6px; border: none;
                   font-size: 13px; font-weight: 600; cursor: pointer;
                   transition: all 0.2s; }
#btn-prev { background: #374151; color: #d1d5db; }
#btn-play { background: #2563eb; color: white; }
#btn-next { background: #374151; color: #d1d5db; }
#btn-play.playing { background: #dc2626; }
#event-counter { font-size: 12px; color: #6b7280; }

/* 动画 */
@keyframes fadeSlideIn { from { opacity:0; transform:translateX(-10px); }
                         to { opacity:1; transform:translateX(0); } }
@keyframes bubbleIn { from { opacity:0; transform:translateY(20px); }
                      to { opacity:1; transform:translateY(0); } }
@keyframes fadeIn { from { opacity:0; } to { opacity:1; } }
@keyframes pulseGlow { 0%,100% { box-shadow: 0 0 5px rgba(37,99,235,0.3); }
                       50% { box-shadow: 0 0 25px rgba(37,99,235,0.8); } }
.fork-pulse { animation: pulseGlow 1.5s ease infinite; }
</style>
</head>
```

#### 8.1.2 HTML Body 结构

```html
<body>
<!-- 顶部时间轴 -->
<div id="timeline">
  <div class="step-label">T0 背景</div>
  <div class="step-dot" data-step="0">T0</div>
  <div id="step-connector"></div>
  <div class="step-dot" data-step="1">T1</div>
  <div id="step-connector"></div>
  <div class="step-dot" data-step="2">T2</div>
  <div id="step-connector"></div>
  <div class="step-dot" data-step="3">T3</div>
  <div id="step-connector"></div>
  <div class="step-dot" data-step="4">T4</div>
  <div id="step-connector"></div>
  <div class="step-dot" data-step="5">T5</div>
  <div id="step-connector"></div>
  <div class="step-dot" data-step="6">T6</div>
  <div class="step-label">终局</div>
</div>

<!-- 三栏主体 -->
<div id="main">
  <div id="memoria-log">
    <h3>🧠 Memoria 操作日志</h3>
    <div id="mem-events"></div>
  </div>
  <div id="debate-area">
    <div id="branch-main" class="branch-section">
      <span class="branch-header main">🌳 main</span>
      <div class="agent-grid" id="grid-main"></div>
    </div>
  </div>
  <div id="drift-panel">
    <h3>🔀 认知漂移对比</h3>
    <div id="drift-cards"></div>
  </div>
</div>

<!-- 底部控制栏 -->
<div id="controls">
  <button id="btn-prev">⏮ 上一事件</button>
  <button id="btn-play">▶ 播放</button>
  <button id="btn-next">下一事件 ⏭</button>
  <span id="event-counter">0 / 0</span>
  <input type="range" id="speed-slider" min="200" max="3000" value="1000"
         style="width:120px;">
  <span id="speed-label">1.0s</span>
</div>
```

#### 8.1.3 JavaScript 动画引擎

```html
<script>
// ── 事件数据（由 Python 注入） ──
const EVENTS = __EVENTS_JSON__;

// ── 状态 ──
let cursor = -1;
let playing = false;
let timer = null;
let speed = 1000;
const branchColors = {
  main: '#3b82f6', control: '#4ade80', contagion: '#f87171',
  fdic_enough: '#c084fc', systemic: '#ef4444'
};

// ── DOM 引用 ──
const memLog = document.getElementById('mem-events');
const debateArea = document.getElementById('debate-area');
const driftCards = document.getElementById('drift-cards');
const btnPlay = document.getElementById('btn-play');
const btnPrev = document.getElementById('btn-prev');
const btnNext = document.getElementById('btn-next');
const counter = document.getElementById('event-counter');
const speedSlider = document.getElementById('speed-slider');
const speedLabel = document.getElementById('speed-label');

counter.textContent = `0 / ${EVENTS.length}`;

// ── 工具函数 ──
function riskClass(conf) {
  if (conf >= 75) return 'risk-critical';
  if (conf >= 50) return 'risk-high';
  if (conf >= 25) return 'risk-medium';
  return 'risk-low';
}

function ensureBranchSection(branch) {
  let sec = document.getElementById('branch-' + branch);
  if (!sec) {
    sec = document.createElement('div');
    sec.id = 'branch-' + branch;
    sec.className = 'branch-section';
    sec.innerHTML = `<span class="branch-header ${branch} fork-pulse">
                       🌿 ${branch}</span>
                     <div class="agent-grid" id="grid-${branch}"></div>`;
    debateArea.appendChild(sec);
  }
  return sec;
}

function addMemEvent(type, text) {
  const div = document.createElement('div');
  div.className = 'mem-event ' + type;
  div.textContent = text;
  memLog.appendChild(div);
  memLog.scrollTop = memLog.scrollHeight;
}

// ── 事件处理器 ──
const handlers = {
  step_start(e) {
    document.querySelectorAll('.step-dot').forEach(d => {
      const s = parseInt(d.dataset.step);
      if (s < e.step) d.className = 'step-dot done';
      else if (s === e.step) d.className = 'step-dot active';
      else d.className = 'step-dot';
    });
    addMemEvent('snapshot', `⏱ T${e.step}: ${e.label || ''}`);
  },

  agent_vote(e) {
    const grid = document.getElementById('grid-' + e.branch) ||
                 ensureBranchSection(e.branch).querySelector('.agent-grid');
    const bubble = document.createElement('div');
    bubble.className = `agent-bubble ${riskClass(e.confidence)}`;
    bubble.style.animationDelay = (Math.random() * 0.3) + 's';
    bubble.innerHTML = `
      <div class="agent-name">${e.agent}</div>
      <div class="verdict">${e.verdict || ''}</div>
      <div class="confidence-bar">
        <div class="confidence-fill" style="width:${e.confidence}%"></div>
      </div>`;
    grid.appendChild(bubble);
    grid.scrollTop = grid.scrollHeight;
  },

  consensus(e) {
    const grid = document.getElementById('grid-' + e.branch);
    if (!grid) return;
    const box = document.createElement('div');
    box.style.cssText = 'background:#1f2937;padding:12px;border-radius:8px;' +
      'margin:8px 0;border-left:4px solid ' + (branchColors[e.branch]||'#666');
    box.innerHTML = `<strong>📊 共识 (${e.branch})</strong><br>
      平均信心: ${e.avg_confidence}%&emsp;
      判定: <span style="color:${e.action==='archive'?'#ef4444':'#4ade80'}">
      ${e.action}</span>`;
    grid.appendChild(box);
  },

  fork(e) {
    addMemEvent('fork', `🔀 分叉: ${e.parent} → ${e.children.join(' + ')}`);
    e.children.forEach(c => ensureBranchSection(c));
    // 闪烁效果
    e.children.forEach(c => {
      const hdr = document.querySelector(`#branch-${c} .branch-header`);
      if (hdr) { hdr.classList.add('fork-pulse');
        setTimeout(() => hdr.classList.remove('fork-pulse'), 3000); }
    });
  },

  snapshot(e) {
    addMemEvent('snapshot', `📸 快照: ${e.branch} @ T${e.step}`);
  },

  archive(e) {
    addMemEvent('archive', `⚰️ 归档: ${e.branch} (信心过低)`);
    const sec = document.getElementById('branch-' + e.branch);
    if (sec) sec.classList.add('archived-overlay');
  },

  rollback(e) {
    addMemEvent('rollback',
      `⏪ 回滚: ${e.branch} → T${e.to_step} 快照`);
  },

  diff(e) {
    addMemEvent('diff', `📊 对比: ${e.branch_a} vs ${e.branch_b}`);
    if (e.comparisons) {
      e.comparisons.forEach(c => {
        const card = document.createElement('div');
        card.className = 'drift-card';
        card.innerHTML = `
          <div class="agent">${c.agent}</div>
          <div class="branch-a">🌿 ${e.branch_a}: ${c.verdict_a || ''}</div>
          <div class="arrow">▼ 认知漂移 ▼</div>
          <div class="branch-b">🔴 ${e.branch_b}: ${c.verdict_b || ''}</div>`;
        driftCards.appendChild(card);
      });
    }
  },

  merge(e) {
    addMemEvent('merge', `🧬 合并: ${e.source} → ${e.target}`);
    const sec = ensureBranchSection(e.target);
    const hdr = sec.querySelector('.branch-header');
    if (hdr) {
      hdr.classList.add('fork-pulse');
      setTimeout(() => hdr.classList.remove('fork-pulse'), 3000);
    }
    const card = document.createElement('div');
    card.className = 'drift-card';
    card.innerHTML = `
      <div class="agent">终局收束</div>
      <div class="branch-a">🌿 胜出分支: ${e.source}</div>
      <div class="arrow">▼ lesson merge ▼</div>
      <div class="branch-b">🌳 主线 ${e.target}: ${e.lesson || ''}</div>`;
    driftCards.prepend(card);
  }
};

// ── 播放控制 ──
function processEvent(idx) {
  if (idx < 0 || idx >= EVENTS.length) return;
  const e = EVENTS[idx];
  const handler = handlers[e.type];
  if (handler) handler(e);
  cursor = idx;
  counter.textContent = `${cursor + 1} / ${EVENTS.length}`;
}

function next() {
  if (cursor + 1 < EVENTS.length) processEvent(cursor + 1);
  else stop();
}
function prev() {
  // 回退 = 重放到 cursor-1
  if (cursor <= 0) return;
  const target = cursor - 1;
  resetUI();
  for (let i = 0; i <= target; i++) processEvent(i);
}
function play() {
  if (playing) { stop(); return; }
  playing = true;
  btnPlay.textContent = '⏸ 暂停';
  btnPlay.classList.add('playing');
  timer = setInterval(next, speed);
}
function stop() {
  playing = false;
  btnPlay.textContent = '▶ 播放';
  btnPlay.classList.remove('playing');
  clearInterval(timer);
}
function resetUI() {
  cursor = -1;
  memLog.innerHTML = '';
  debateArea.innerHTML = `<div id="branch-main" class="branch-section">
    <span class="branch-header main">🌳 main</span>
    <div class="agent-grid" id="grid-main"></div></div>`;
  driftCards.innerHTML = '';
  document.querySelectorAll('.step-dot').forEach(d => d.className = 'step-dot');
}

btnPlay.addEventListener('click', play);
btnNext.addEventListener('click', next);
btnPrev.addEventListener('click', prev);
speedSlider.addEventListener('input', () => {
  speed = parseInt(speedSlider.value);
  speedLabel.textContent = (speed / 1000).toFixed(1) + 's';
  if (playing) { clearInterval(timer); timer = setInterval(next, speed); }
});
</script>
</body>
</html>
```

### 8.2 主入口

```python
# main.py
import logging, sys, os, json

log = logging.getLogger("main")

def _setup_logging():
    """必须在 output/ 目录创建之后调用"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("output/pipeline.log", mode="w"),
        ],
    )

def check_env():
    """检查必要环境变量"""
    required = ["LLM_API_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        log.error(f"缺少环境变量: {missing}")
        log.error("请复制 .env.example 为 .env 并填入配置")
        sys.exit(1)

    memoria_url = os.getenv("MEMORIA_URL", "http://127.0.0.1:3100")
    try:
        import requests
        resp = requests.get(f"{memoria_url}/v1/branches", timeout=5)
        resp.raise_for_status()
        log.info(f"✓ Memoria 服务正常 ({memoria_url})")
    except Exception as e:
        log.error(f"✗ 无法连接 Memoria: {memoria_url} — {e}")
        log.error("请先启动: memoria --db-url <your_db_url>")
        sys.exit(1)

def main():
    os.makedirs("output", exist_ok=True)  # 必须在 FileHandler 之前
    _setup_logging()

    # 加载 .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    check_env()

    # ── 第一阶段：数据准备 ──
    log.info("\n📦 第一阶段：数据准备")
    from data.fetch_gdelt import main as fetch_gdelt
    from data.fetch_market import main as fetch_market
    from data.build_seeds import main as build_seeds

    fetch_gdelt()
    fetch_market()
    build_seeds()

    # ── 第二阶段：运行回测 ──
    log.info("\n🚀 第二阶段：运行多 Agent 回测")
    from orchestrator.main_loop import Orchestrator
    from events.recorder import EventRecorder
    recorder = EventRecorder("output/events.json")
    orch = Orchestrator(recorder=recorder)
    report = orch.run()

    # ── 第三阶段：校准与验证 ──
    log.info("\n📐 第三阶段：校准与事后验证")
    from calibration.scorer import calibrate
    from calibration.ground_truth import validate
    from memoria.client import MemoriaClient
    calibration = calibrate(orch.results)
    validation = validate(calibration)
    json.dump(validation, open("output/validation.json", "w"), ensure_ascii=False, indent=2)

    mem = MemoriaClient()

    # ── 第四阶段：Memoria 回溯实验 ──
    log.info("\n🔬 第四阶段：Memoria 回溯实验")
    from calibration.rollback_experiment import run_rollback_demo
    run_rollback_demo(mem, recorder=recorder,
                      active_branches=report.get("surviving_branches", []))

    # ── 第五阶段：终局收束，胜出分支 merge 回 main ──
    log.info("\n🏁 第五阶段：终局收束（Merge 回主线）")
    from calibration.epilogue import merge_winner_back
    epilogue = merge_winner_back(mem, validation, recorder=recorder, target="main")
    json.dump(epilogue, open("output/epilogue.json", "w"), ensure_ascii=False, indent=2)

    # 回写最终报告，使其包含终局 merge 结果
    report["epilogue"] = epilogue
    json.dump(report, open("output/final_report.json", "w"), ensure_ascii=False, indent=2)

    # ── 回测 + 回溯 + merge 全部完成，写盘后再生成 Dashboard ──
    recorder.save()

    # ── 第六阶段：生成叙事 Dashboard ──
    log.info("\n📊 第六阶段：生成叙事 Dashboard")
    from output.dashboard import generate_dashboard
    generate_dashboard("output/events.json", "output/dashboard.html")

    log.info("\n" + "=" * 60)
    log.info("✅ Pipeline 完成！")
    log.info("=" * 60)
    log.info("输出文件:")
    log.info("  📄 output/final_report.json   — 最终分析报告")
    log.info("  📄 output/validation.json     — 与真实历史的校准对比")
    log.info("  📄 output/epilogue.json       — 胜出分支 merge 收束结果")
    log.info("  📄 output/events.json         — 结构化事件日志")
    log.info("  🎬 output/dashboard.html      — 交互式叙事 Dashboard")
    log.info("  📄 output/pipeline.log        — 完整运行日志")

if __name__ == "__main__":
    main()
```

### 8.3 一键运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 LLM_API_KEY

# 3. 启动 Memoria（另一个终端）
memoria --db-url "mysql://user:pass@host:6001/memoria" \
        --transport http --port 3100

# 4. 一键运行
python main.py
```

### 8.4 requirements.txt

```
requests>=2.28
pandas>=1.5
gdeltdoc>=1.0
yfinance>=0.2
python-dotenv>=1.0
```

### 8.5 .env.example

```env
# LLM 配置（阿里云 DashScope）
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=your_dashscope_api_key_here
LLM_MODEL=qwen-plus

# Memoria 服务地址
MEMORIA_URL=http://127.0.0.1:3100
```

---

## 9. Memoria 推广价值评估

### 为什么这个 Demo 能体现 Memoria 的不可替代性？

**其他记忆系统（mem0 / MemOS / HydraDB）能做到的：**
- ✅ 存储 Agent 的历史判断
- ✅ 语义检索相关记忆
- ✅ 基本的读写操作

**只有 Memoria 能做到的：**
- ✅ **分支（Branch）**：Agent 分歧涌现时自动分叉——不是预设剧本，而是 12 个 Agent 真实投票极化后系统自动创建 2-4 条平行世界
- ✅ **快照（Snapshot）**：每个时间步自动存档，7步×N分支 = 完整的决策历史胶片
- ✅ **回滚（Rollback）**：回到任意分叉点重新决策——如果当初走了另一条路会怎样？
- ✅ **差异对比（Diff）**：直观展示两个情景分支的记忆如何分化
- ✅ **合并（Merge）**：将获胜分支的经验合并回主线，形成组织记忆

### 涌现式分叉：为什么分歧必须是自发的？

硬编码"在 T2 分叉、在 T5 分叉"的 demo 看起来整洁，但观众会想："这不就是你手写的 if-else 吗？"

本 Pipeline 采用**涌现式分叉**：
1. 每步跑完 12 个 Agent 后，计算投票极化指数和标准差
2. 当极化 ≥ 40 且标准差 ≥ 15 时，按 `contagion_risk` 聚类
3. 每个拥有 ≥ 2 人的派系自动成为一条分支（2-4 条不等）
4. 活跃分支上限 8 条，防止爆炸

**效果差异**：每次运行可能在不同步骤分叉、产生不同数量的分支。
T0 可能完全一致，T2 可能三派鼎立，T4 可能意外平静。
这才是真正的"分歧从分歧中涌现"，Memoria 的分支能力不是装饰，而是必须。

### 叙事 Dashboard 为何让人眼前一亮？

传统 demo 的呈现方式是"跑完输出一堆 JSON + 几张静态图表"，观众只看到**结果**，看不到**过程**。

本 Pipeline 的 Dashboard 把全部决策过程压缩成一部**可交互回放的 6 幕动画**：

| 幕 | 对应步骤 | 视觉效果 | Memoria 操作 |
|----|----------|----------|-------------|
| 序幕 | T0-T1 | 12 个 Agent 气泡从下方浮入，意见趋同 | store 初始判断 |
| 分裂 | 首次分歧涌现 | 极化指标突破阈值，时间轴分叉成 2-4 列 | branch + snapshot |
| 发酵 | 后续步骤 | 气泡颜色随信心漂移渐变，分支数动态增减 | 各分支 store + snapshot |
| 清算 | 信心跌破阈值 | 低信心分支灰色覆盖淡出，校准教训浮现 | archive + 可能的再次分叉 |
| 回溯 | 回滚实验 | 倒带动画 + 对比面板亮起 | rollback + diff |
| 归一 | 终局收束 | main 分支重新点亮，胜出路径高亮保留 | merge + lesson 回写 |

**关键区别**：观众不是在看"Memoria 存了什么"，而是**亲眼看到分支记忆如何改变了决策走向**。
左栏的 Memoria 操作日志与中央的 Agent 辩论同步推进，右栏的认知漂移对比让"有 vs 没有分支记忆"的差异一目了然。

### 最后 90 秒的高潮脚本

要把这个 Demo 从“解释 Memoria 有用”推进到“让观众当场记住”，结尾不能停在 `diff` 面板亮起，而要完成一个**回滚 -> 重放 -> 合并回主线**的闭环。

建议把现场演示的最后 90 秒固定成下面 4 个镜头：

1. **冻结在首个分叉点快照**
   屏幕上暂停在分歧涌现的那个时间步。左侧日志停在 `snapshot(...__T?_prefork)`，中间是意见激烈分化的 Agent 气泡——有人坚信风险可控，有人认为危机正在蔓延。
   讲解词：
   > "注意，这个分叉不是我预设的。是 12 个 Agent 的投票极化超过了阈值，系统自动触发了分叉。每次运行，分叉可能出现在不同步骤、产生不同数量的分支。"

2. **一键回滚，时间线倒带**
   触发 `rollback` 后，顶部时间轴从末端倒退回分叉点，右侧 `diff` 面板同时亮起，把分叉前后的判断差异并排展开。
   讲解词：
   > "这不是重新生成一段总结，而是把整套记忆状态退回那个时间点。Agent 将带着当时的记忆重新往后推演。"

3. **重放后续步骤，让错误世界线被证伪**
   继续播放后，信心不足的分支逐步灰化、归档；高信心分支保持高亮。此时对比卡片显示同一个 Agent 在不同分支上的判断如何分化。
   讲解词：
   > "同一批 Agent、同一套角色，只因为历史记忆不同，后续判断就开始系统性分叉。这就是 branchable memory 的价值，不是提示词技巧。"

4. **把胜出分支 merge 回 `main`，完成收束**
   最后高亮最终胜出的分支，将其 lesson 和关键判断合并回 `main`。画面上 `main` 分支重新点亮，被证伪的分支保持灰化，日志出现 `merge(winner -> main)`。
   讲解词：
   > "真正重要的不是我们做过多少分叉，而是失败路径被保留为教训，胜出路径被吸收成主线记忆。Memoria 不是把历史存起来，而是把组织的认知演化管理起来。"

### 为什么这个结尾能把效果拉到 9 分附近？

因为它最终展示的不再是“我有 branch / snapshot / rollback 这些 API”，而是一个**没有 Memoria 就很难自然完成的动作链**：

- 先冻结某个历史认知状态
- 再从那个状态重放后续世界线
- 然后直观看到分支如何分化
- 最后把胜出路径并回主线，把失败路径保留为 lesson

当观众看到最后一步 `merge back to main` 时，才会真正意识到：
Memoria 不是普通的 memory store，而是**版本化的集体认知系统**。

### 一句话总结

> **没有 Memoria 的分支/快照能力，12 个 Agent 的投票分歧只是一堆散乱的日志。有了它，分歧自动涌现为分支、被证伪的路径归档为教训、胜出路径合并回主线。涌现式分叉让每次运行都不可预测——观众亲眼看到"不是你设定了分叉，而是 Agent 自己吵出了分叉"，这就是 branchable memory 的必须性。交互式叙事 Dashboard 则让这一切从"技术上可行"变成"肉眼可见、当场可感"。**

---

*文档版本：自动化 Pipeline 设计稿 v4.0（涌现式分叉 + 叙事 Dashboard）*
*核心依赖：Memoria v0.2.0 + qwen-plus + GDELT + Yahoo Finance*
