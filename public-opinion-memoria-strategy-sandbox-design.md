# 社会舆论事件策略沙盘设计稿

## 1. 文档目的

本文档定义一个基于 `Agent + Memoria` 的社会舆论事件策略研究工具，并给出：

- 产品目标与价值主张
- 设计思路与核心概念
- 状态转移与收敛定义
- 群体画像与记忆结构
- 具体案例设定
- 演示 Demo 设计
- 可直接落地的代码骨架

这不是一个“舆情预测神谕”，而是一个：

`可分叉、可回溯、可审计的社会认知事件演化沙盘`

它面向的核心问题是：

`当企业遭遇社会事件时，如何在发布真实公告前，先对不同回应策略做多轮推演，并比较哪条路径更可能收敛到更好的结果。`

---

## 2. 最终要做成什么

### 2.1 产品定义

系统输入：

- 一个具体社会事件
- 一组高权重舆论群体画像
- 群体的初始记忆与认知倾向
- 一系列外部事件与公司可选动作

系统输出：

- 每一轮各群体的判断、情绪、动作
- 群体之间的影响传播
- 不同公司策略下的分叉演化路径
- 收敛或失控的轨迹对比
- 可回放、可审计、可比较的完整过程记录

### 2.2 目标用户

- 企业公关与传播负责人
- 品牌风险管理团队
- 研究型咨询团队
- 战略决策层
- 舆情分析工具产品团队

### 2.3 核心价值

#### 对外部观众

它证明 `Memoria` 不是普通 memory store，而是：

`多主体认知版本控制系统`

#### 对实际业务

它允许团队在真实发声前做“策略压力测试”：

- 先试演
- 再比较
- 再决定

#### 对演示 Demo

它能把抽象的 `branch / snapshot / rollback / diff / merge` 变成肉眼可见的社会认知演化。

---

## 3. 核心设计思路

### 3.1 设计原则

1. `个体记忆是真实状态，共识点只是聚合视图`
2. `每个群体都有自己的连续记忆轨迹`
3. `每一轮不仅有判断，还有动作`
4. `动作会影响其他群体`
5. `公司回应是显式的人工决策检查点`
6. `系统必须支持回溯、对比、分叉与合并`

### 3.2 最重要的概念澄清

#### Agent / 群体

每个 Agent 代表一类高权重舆论群体，而不是单个真实用户。

例如：

- 核心用户
- 普通消费者
- 行业媒体
- 激进维权者
- 中立围观者
- 品牌粉丝
- 投资人
- 监管关注者

#### 个体记忆

每个群体在每个时间点都有自己的记忆上下文。它包括：

- 固有画像
- 历史事件解释
- 历史情绪变化
- 历史动作记录
- 对其他群体和公司动作的反应

#### 共识点

共识点不是 memory 本体，也不是“这群人拥有同一份记忆”。

共识点是：

`某一轮里，若干拥有不同记忆轨迹的群体，在判断与动作上暂时收敛形成的聚类节点`

所以：

- `memory` 是因
- `judgment + action` 是果
- `共识点` 是对“果”的压缩视图

#### 公司决策检查点

真实世界里，公众不会真的停下来等公司回应。

但在沙盘中，我们必须显式插入一个：

`公司决策检查点`

正确机制不是“所有人傻等公司”，而是：

1. 事件先触发一轮群体自发反应
2. 群体之间发生一轮影响
3. 系统暂停
4. 用户扮演公司，选择动作或选择沉默
5. 系统再进入下一轮

这样兼顾真实性和可操作性。

---

## 4. 这套系统到底证明什么

它证明：

`仅靠 Agent + Memoria，可以构建一个多步推进、可分叉、可回溯、可审计的社会认知事件演化系统。`

注意这不是严格数值意义上的现实世界仿真器。

它演化的是：

- 认知
- 判断
- 情绪
- 动作
- 阵营形成
- 路径分叉
- 策略后果

它不直接替代：

- 真实平台推荐机制
- 真实转发网络扩散模型
- 真实交易系统
- 现实监管流程本体

所以它的定位应是：

`策略研究工具`

而不是：

`真实性保证的预测机器`

---

## 5. 系统目标与非目标

### 5.1 产品目标

1. 支持多轮舆论事件演化
2. 支持多个高权重群体的独立记忆和动作
3. 支持用户在关键节点注入公司策略
4. 支持策略分叉与平行推演
5. 支持 rollback / diff / merge
6. 支持可视化回放与演示
7. 支持可审计的状态追踪

### 5.2 非目标

1. 不试图预测每一个真实网友的行为
2. 不试图还原真实平台的全部传播机制
3. 不把 MBTI 当成唯一人格建模方法
4. 不承诺“模拟结果必然等于现实”

---

## 6. 实体定义

### 6.1 群体画像 Group Profile

每个群体必须拥有一组舆情相关维度，而不是只用 MBTI。

建议字段：

```python
from dataclasses import dataclass, field

@dataclass
class GroupProfile:
    group_id: str
    name: str
    archetype: str
    share_weight: float
    baseline_trust: float          # 对品牌基础信任
    fairness_sensitivity: float    # 对欺骗/不公的敏感度
    risk_aversion: float           # 风险厌恶程度
    conformity: float              # 从众倾向
    action_threshold: float        # 从情绪到行动的门槛
    official_trust: float          # 对官方声明的信任
    media_trust: float             # 对媒体/KOL的信任
    regulator_trust: float         # 对监管部门的信任
    identity_binding: float        # 是否与品牌强身份绑定
    style_tags: list[str] = field(default_factory=list)
```

`MBTI` 可以作为 `style_tags` 的 flavor，但不能成为核心状态机输入。

### 6.2 记忆条目 Memory Entry

```python
@dataclass
class MemoryEntry:
    step_id: str
    timestamp: str
    entry_type: str
    content: dict
```

`entry_type` 可以是：

- `profile_seed`
- `event_input`
- `judgment`
- `emotion_update`
- `group_action`
- `peer_influence`
- `company_action`
- `snapshot_marker`
- `branch_hypothesis`

### 6.3 群体状态 Group State

```python
@dataclass
class GroupState:
    group_id: str
    stance: str                    # 当前立场
    confidence: float              # 判断置信度
    emotion: str                   # 愤怒/怀疑/支持/冷漠等
    emotion_intensity: float
    action: str                    # 本轮采取的动作
    action_intensity: float
    influence_score: float         # 对其他群体的影响力
```

### 6.4 公司动作 Company Action

```python
@dataclass
class CompanyAction:
    action_id: str
    label: str
    tone: str
    transparency: float
    responsibility_level: float
    compensation_level: float
    speed: float
    actor: str                     # 官号 / CEO / 法务 / 第三方
```

动作集合建议：

- `silence`
- `brief_response`
- `apology`
- `deny`
- `shift_blame`
- `compensate`
- `recall_or_suspend`
- `ceo_video_statement`
- `third_party_audit`
- `report_to_regulator`

### 6.5 共识聚合视图 Consensus Cluster

```python
@dataclass
class ConsensusCluster:
    cluster_id: str
    step_id: str
    label: str                     # 例如“观望但怀疑官方”
    dominant_action: str
    share: float                   # 占总权重比例
    emotion_signature: str
    member_group_ids: list[str]
```

重要：

`cluster` 只是某一步的聚合视图，不是基础状态容器。

---

## 7. 初始记忆如何建立

初始记忆不是“过去新闻摘要”，而是群体的：

- 性格倾向
- 认知维度
- 品牌历史经验
- 过往类似事件的经验模板
- 对不同信息源的信任分布

例如：

```python
initial_memory = [
    {
        "entry_type": "profile_seed",
        "content": {
            "baseline_trust": 0.35,
            "fairness_sensitivity": 0.92,
            "action_threshold": 0.38,
            "style_tags": ["skeptical", "consumer-rights", "highly-reactive"]
        }
    }
]
```

初始记忆决定的是：

`相同外部信息进入时，不同群体如何解释它。`

---

## 8. 每一轮演化机制

### 8.1 轮次结构

每一轮固定采用如下顺序：

1. `新增事件进入`
2. `各群体基于记忆解释事件`
3. `各群体输出判断与情绪`
4. `各群体选择动作`
5. `群体动作相互影响`
6. `进入公司决策检查点`
7. `用户选择公司动作或选择沉默`
8. `将本轮结果写入记忆`
9. `生成下一轮状态与聚合视图`

### 8.2 演化伪代码

```python
def run_round(step, event_input, company_action=None):
    group_outputs = []

    for group in groups:
        memory_context = memoria.retrieve(group.group_id, branch=current_branch)
        judgment = judge_event(group, memory_context, event_input)
        action = choose_action(group, judgment, memory_context)
        group_outputs.append((group, judgment, action))

    influence_updates = compute_peer_influence(group_outputs)

    if company_action is None:
        return PauseForUserDecision(
            step_id=step.step_id,
            group_outputs=group_outputs,
            influence_updates=influence_updates,
        )

    persisted = []
    for group, judgment, action in group_outputs:
        persisted.extend([
            judgment.to_memory_entry(step.step_id),
            action.to_memory_entry(step.step_id),
            influence_updates[group.group_id].to_memory_entry(step.step_id),
            company_action.to_memory_entry(step.step_id),
        ])

    memoria.store_many(group.group_id, persisted, branch=current_branch)
    return build_next_state(step, group_outputs, influence_updates, company_action)
```

### 8.3 为什么“先有动作，再等用户决策”

这是为了让系统保留真实感：

- 公众不会完全静止
- 事件爆出后必然先有一轮自发反应
- 公司真正能够控制的是“下一轮怎么接”

所以沙盘控制权发生在：

`第一轮公众反应之后，下一轮系统推进之前`

---

## 9. 动作系统定义

### 9.1 群体动作集合

群体每轮必须输出显式动作，而不是只给观点。

建议动作枚举：

```python
GROUP_ACTIONS = [
    "wait",
    "discuss",
    "mock",
    "defend",
    "accuse",
    "boycott",
    "report",
    "complain_to_regulator",
    "organize",
    "exit",
]
```

### 9.2 动作的附加属性

每个动作还应带有：

- `target`
- `intensity`
- `broadcast_scope`
- `delay`
- `escalation_level`

例如：

```python
{
    "action": "complain_to_regulator",
    "target": "market_regulator",
    "intensity": 0.81,
    "broadcast_scope": "medium",
    "delay": 1,
    "escalation_level": 0.92
}
```

### 9.3 动作为什么重要

如果只有观点，没有动作，系统只能表达：

`大家怎么看`

有了动作，系统才能表达：

`大家做了什么，这些动作又如何反过来塑造下一轮事件。`

---

## 10. 群体间影响机制

### 10.1 影响对象

一个群体的动作可能影响：

- 其他群体的情绪
- 其他群体的行动门槛
- 其他群体对官方回应的信任
- 其他群体对事件严重性的判断

### 10.2 影响因子

建议至少考虑：

- 发起群体影响力
- 被影响群体的信任结构
- 两个群体的相似性
- 动作类型与强度
- 是否有延迟生效

### 10.3 影响示意

```python
def apply_influence(source_state, target_profile, target_state):
    trust_factor = target_profile.media_trust if source_state.action in {"mock", "accuse"} else target_profile.official_trust
    delta = source_state.action_intensity * source_state.influence_score * trust_factor
    target_state.emotion_intensity = min(1.0, target_state.emotion_intensity + delta * 0.2)
    return target_state
```

---

## 11. 公司决策检查点

### 11.1 定义

每一轮群体自发演化结束后，系统进入暂停态。

此时页面必须显式展示：

- 当前主导情绪
- 当前主导动作
- 升级中的关键群体
- 可回拉的中间群体
- 上一轮到这一轮的变化

然后由用户在 UI 中选择公司动作。

### 11.2 沉默也是动作

在这个系统里，沉默不是“无事发生”，而是：

`一种明确策略`

它必须被写入记忆，并影响下一轮推演。

### 11.3 为什么要用户手动操作

因为这个系统要成为：

`策略研究工具`

而不是无人干预的自动剧情播放器。

用户必须在关键节点真实做出选择，这样 rollback 和分叉才有意义。

---

## 12. 分叉、回溯、对比、合并

### 12.1 分叉 Branch

在同一个决策检查点，用户可以选择多种公司动作，并将它们分别演化为不同路径。

例如：

- `main/T2/apology`
- `main/T2/silence`
- `main/T2/deny`

### 12.2 快照 Snapshot

在每个关键点写入：

- 轮次前快照
- 公司动作前快照
- 收敛前快照

用途：

- 回滚
- 对比
- 生成时间轴

### 12.3 回滚 Rollback

当某条路径持续恶化时，用户可以：

- 回到某个快照
- 重新选择不同的公司动作
- 再次向前推演

### 12.4 差异对比 Diff

比较对象包括：

- 两个分支的群体动作分布
- 两个分支的情绪结构
- 两个分支的共识点数量与主导态
- 两个分支的收敛速度与风险级别

### 12.5 合并 Merge

当某条路径表现显著更好时，可以把该路径的策略结论合并回主线。

这里的 merge 不是“删除失败路径”，而是：

`把当前最有价值的认知结果吸收到主线决策记录中。`

---

## 13. 收敛定义

### 13.1 为什么不能只看“80% 群体同一动作”

这个条件太粗。

因为可能出现：

- 大家都在骂，但强度还在升级
- 群体动作看似一致，但监管类动作正在酝酿
- 主导动作一致，但关键高影响群体仍在转向

### 13.2 建议收敛条件

至少满足以下三类指标：

1. `主导动作占比足够高`
2. `动作变化率持续下降`
3. `高风险动作显著回落`

### 13.3 形式化定义

```python
def is_converged(history):
    latest = history[-1]
    prev = history[-2] if len(history) > 1 else None

    dominant_ok = latest.dominant_action_share >= 0.70
    escalation_ok = latest.high_risk_action_share <= 0.15
    stability_ok = prev is not None and abs(latest.dominant_action_share - prev.dominant_action_share) <= 0.05

    return dominant_ok and escalation_ok and stability_ok
```

### 13.4 终止条件

系统可在以下任一条件下终止：

- 达到收敛
- 达到最大轮数
- 风险分数超过阈值，判定为失控
- 用户主动停止并回滚

---

## 14. 具体案例建议

### 14.1 为什么不用 SVB 作为主场景

SVB 更适合证明“认知分叉”，但如果产品定位是企业策略沙盘，最佳主场景应更接近企业真实操作。

### 14.2 推荐主场景

`某新消费品牌被曝食品安全问题，公司需要在 48 小时内制定回应策略`

### 14.3 参与群体

建议 8 个群体：

1. 核心粉丝用户
2. 普通消费者
3. 维权型消费者
4. 中立围观者
5. 行业媒体
6. 大 V / KOL
7. 监管关注者
8. 投资人/合作渠道

### 14.4 时间线

- `T0` 爆料帖出现
- `T1` 热搜发酵，KOL 跟进
- `T2` 第一轮公司决策检查点
- `T3` 公司第一轮回应后的演化
- `T4` 监管/第三方消息进入
- `T5` 第二轮公司决策检查点
- `T6` 收敛、缓和或二次爆炸

### 14.5 策略分叉示例

在 `T2` 可测试：

- 仅发简短回应
- 先道歉后说明
- 否认并强调谣言
- 沉默等待更多信息
- 先下架再说明
- 邀请第三方检测

在 `T5` 可继续测试：

- CEO 出镜
- 补偿方案
- 更换供应商
- 启动监管协作声明

---

## 15. 演示 Demo 设计

### 15.1 演示目标

Demo 不是为了展示一个漂亮的流程图，而是为了让用户肉眼看懂：

1. 相同事件如何被不同群体不同解释
2. 群体如何形成判断簇
3. 群体动作如何推动局势演化
4. 公司不同动作如何导致不同路径
5. 为什么这需要 Memoria 的可回溯状态管理

### 15.2 核心表现层原则

#### 无限画布

整个演示必须基于：

`一张无限大的画布`

原因：

- 共识点会持续向未来延伸
- 不同策略会在画布上产生新的路径
- rollback 和 merge 需要跨时间跨度可视化

#### 焦点跟随最新共识聚合视图

相机焦点不应固定在左上角，而应：

`始终平滑跟随最新生成出的共识聚合视图`

这意味着：

- 当新节点在更远处生成时，相机跟过去
- 当发生 merge 时，相机拉回主线
- 当 rollback 时，相机沿时间轴倒退

#### 每个聚合视图都是一个圆点

每一个共识聚合视图都显示为一个圆点，圆点上必须可见：

- 当前共识状态
- 主导动作
- 群体占比
- 情绪色彩

示意：

```json
{
  "cluster_id": "T3_cluster_2",
  "label": "观望但对官方失去信任",
  "dominant_action": "discuss",
  "share": 0.28,
  "emotion": "skeptical"
}
```

### 15.3 画面结构

建议三栏布局：

1. `左侧`
   当前轮的群体发言气泡与动作卡片
2. `中间`
   无限画布上的共识点演化主视图
3. `右侧`
   当前状态、群体统计、公司决策面板、Memoria 状态面板

### 15.4 单轮镜头语言

每一轮应遵循以下表现顺序：

1. 新事件进入
2. 左侧出现多个群体发言与动作气泡
3. 气泡被吸入画布中的目标共识点
4. 旧点向新点缓慢生长出连线
5. 表示群体占比的 token 沿线迁移
6. 新共识点逐渐亮起
7. 系统停在公司决策检查点
8. 用户选择公司动作
9. 继续推进下一轮

### 15.5 必须显示的 Memoria 状态层

如果只有动画，没有状态层，观众看不到 Memoria 的价值。

所以必须有一个显式 `Memoria State` 面板，至少显示：

- 当前 branch
- 当前 snapshot
- 本轮新增 memory entries 数量
- 最近一次 rollback 目标
- 最近一次 diff 对比对象
- 当前主线/实验线状态

### 15.6 Rollback 镜头

当用户触发回滚时：

- 时间轴反向扫回
- 未来路径变暗
- 相机回到目标快照节点
- 状态面板显示 `rollback(to=T2_snapshot)`

### 15.7 Merge 镜头

当用户选择某条优选路径合并回主线时：

- 优选路径高亮
- 非优选路径降低透明度
- 一条明显的 merge 路径收束回 `main`
- 状态面板显示 `merge(branch_x -> main)`

---

## 16. 为什么这个 Demo 能体现 Memoria 价值

如果只有群体演化，观众只能看到“社会事件动画”。

要让 Memoria 的价值出现，必须显式证明：

1. 同一群体在不同分支记忆下会做出不同判断
2. rollback 后系统真的回到旧状态
3. diff 真的是两个认知路径之间的差异
4. merge 真的是把优选结论吸收回主线

所以这个 Demo 的真正证明链是：

`事件 -> 群体记忆驱动判断 -> 群体形成聚合共识 -> 用户注入公司策略 -> 状态被快照/分叉 -> 结果可比较 -> 路径可回滚 -> 优选结论可合并`

---

## 17. 实现架构

### 17.1 模块划分

```text
strategy_sandbox/
  app.py
  domain/
    profiles.py
    memory.py
    actions.py
    clusters.py
    convergence.py
  engine/
    round_engine.py
    influence_engine.py
    branching_engine.py
    scoring_engine.py
  adapters/
    memoria_adapter.py
    mock_memoria_adapter.py
    real_memoria_adapter.py
  scenarios/
    food_safety_case.py
  demo/
    scene_builder.py
    camera_controller.py
    dashboard_template.html
  output/
    state_log.json
    graph.json
    dashboard.html
```

### 17.2 Memoria 适配层

为了便于先做伪数据 demo，再接真实 Memoria，必须抽象统一接口：

```python
class MemoriaAdapter:
    def store_many(self, group_id: str, entries: list[dict], branch: str) -> None:
        raise NotImplementedError

    def retrieve(self, group_id: str, branch: str) -> list[dict]:
        raise NotImplementedError

    def snapshot(self, branch: str, label: str) -> str:
        raise NotImplementedError

    def branch(self, source_branch: str, new_branch: str, label: str) -> str:
        raise NotImplementedError

    def rollback(self, branch: str, snapshot_id: str) -> None:
        raise NotImplementedError

    def diff(self, branch_a: str, branch_b: str) -> dict:
        raise NotImplementedError

    def merge(self, source_branch: str, target_branch: str) -> None:
        raise NotImplementedError
```

### 17.3 回合引擎

```python
class RoundEngine:
    def __init__(self, memoria: MemoriaAdapter, groups: list[GroupProfile]):
        self.memoria = memoria
        self.groups = groups

    def simulate_pre_company_phase(self, step_id: str, event_input: dict) -> dict:
        outputs = []
        for group in self.groups:
            memory = self.memoria.retrieve(group.group_id, branch="main")
            judgment = judge_event(group, memory, event_input)
            action = choose_group_action(group, judgment, memory)
            outputs.append({
                "group_id": group.group_id,
                "judgment": judgment,
                "action": action,
            })

        influenced = run_peer_influence(outputs, self.groups)
        clusters = cluster_outputs(influenced, self.groups)
        return {
            "outputs": influenced,
            "clusters": clusters,
            "pause_for_company_action": True,
        }

    def continue_post_company_phase(self, step_id: str, company_action: CompanyAction, phase_state: dict) -> dict:
        for output in phase_state["outputs"]:
            group_id = output["group_id"]
            entries = [
                {"entry_type": "judgment", "content": output["judgment"]},
                {"entry_type": "group_action", "content": output["action"]},
                {"entry_type": "company_action", "content": company_action.__dict__},
            ]
            self.memoria.store_many(group_id, entries, branch="main")

        snapshot_id = self.memoria.snapshot("main", f"{step_id}_post_company")
        return {"snapshot_id": snapshot_id}
```

### 17.4 共识聚类

```python
def cluster_outputs(outputs: list[dict], groups: list[GroupProfile]) -> list[ConsensusCluster]:
    buckets: dict[tuple[str, str], list[str]] = {}

    for item in outputs:
        stance = item["judgment"]["stance"]
        action = item["action"]["action"]
        key = (stance, action)
        buckets.setdefault(key, []).append(item["group_id"])

    group_map = {g.group_id: g for g in groups}
    clusters = []
    for idx, ((stance, action), member_ids) in enumerate(buckets.items()):
        share = sum(group_map[mid].share_weight for mid in member_ids)
        clusters.append(ConsensusCluster(
            cluster_id=f"cluster_{idx}",
            step_id="unknown",
            label=stance,
            dominant_action=action,
            share=round(share, 3),
            emotion_signature=derive_emotion_signature(member_ids),
            member_group_ids=member_ids,
        ))
    return clusters
```

### 17.5 收敛判定器

```python
def evaluate_convergence(round_states: list[dict]) -> dict:
    latest = round_states[-1]
    dominant_share = latest["dominant_action_share"]
    high_risk_share = latest["high_risk_action_share"]
    delta = latest["distribution_delta"]

    converged = (
        dominant_share >= 0.70 and
        high_risk_share <= 0.15 and
        delta <= 0.05
    )
    return {
        "converged": converged,
        "dominant_action_share": dominant_share,
        "high_risk_action_share": high_risk_share,
    }
```

---

## 18. 演示前端代码骨架

### 18.1 无限画布与相机

```javascript
class CameraController {
  constructor() {
    this.x = 0;
    this.y = 0;
    this.scale = 1;
    this.targetX = 0;
    this.targetY = 0;
  }

  follow(node) {
    this.targetX = node.x;
    this.targetY = node.y;
  }

  tick() {
    this.x += (this.targetX - this.x) * 0.08;
    this.y += (this.targetY - this.y) * 0.08;
  }
}
```

### 18.2 共识点节点

```javascript
function renderCluster(ctx, cluster) {
  const radius = 36 + cluster.share * 90;
  ctx.beginPath();
  ctx.arc(cluster.x, cluster.y, radius, 0, Math.PI * 2);
  ctx.fillStyle = cluster.color;
  ctx.fill();

  ctx.fillStyle = "#101418";
  ctx.textAlign = "center";
  ctx.fillText(cluster.label, cluster.x, cluster.y - 4);
  ctx.fillText(`${Math.round(cluster.share * 100)}%`, cluster.x, cluster.y + 14);
}
```

### 18.3 焦点跟随最新视图

```javascript
function updateCameraForScene(scene) {
  const latestCluster = scene.clusters[scene.clusters.length - 1];
  if (latestCluster) {
    camera.follow(latestCluster);
  }
}
```

### 18.4 用户决策检查点

```javascript
function pauseForCompanyAction(roundState) {
  ui.showDecisionPanel({
    dominantEmotion: roundState.dominantEmotion,
    dominantAction: roundState.dominantAction,
    escalatingGroups: roundState.escalatingGroups,
    choices: [
      "silence",
      "brief_response",
      "apology",
      "deny",
      "compensate",
      "ceo_video_statement",
      "third_party_audit",
    ],
  });
}
```

### 18.5 Memoria 状态面板

```javascript
function renderMemoriaOverlay(state) {
  overlay.innerHTML = `
    <div>Branch: ${state.branch}</div>
    <div>Snapshot: ${state.snapshotId}</div>
    <div>Entries Added: ${state.newEntries}</div>
    <div>Last Diff: ${state.lastDiff || "-"}</div>
    <div>Last Rollback: ${state.lastRollback || "-"}</div>
  `;
}
```

---

## 19. Demo 运行模式

### 19.1 Scripted Demo 模式

用于对外展示。

特点：

- 数据可预先编排
- 保证镜头节奏和高潮效果
- 适合发布会、路演、文章 GIF

### 19.2 Simulation 模式

用于内部策略研究。

特点：

- 用户实时选择公司动作
- 每轮重新计算状态
- 允许创建分叉并比较结果

### 19.3 双模式并存

系统应同时支持：

- `MockMemoria + 预置数据` 的导演版演示
- `RealMemoria + 实时推演` 的研究版系统

---

## 20. 最小可行版本 MVP

### 20.1 MVP 范围

1. 8 个群体
2. 6 个时间节点
3. 1 个主事件案例
4. 5 个公司可选动作
5. 1 条主线 + 2 条实验分支
6. rollback / diff / merge 各 1 次
7. 无限画布 + 相机跟随 + 决策检查点

### 20.2 MVP 成功标准

- 用户可以看懂群体如何分化
- 用户可以在检查点手动决策
- 系统可以回滚到旧状态
- 系统可以比较两条策略线
- 观众能明确看到 Memoria 的价值

---

## 21. 实施顺序

### 阶段 1：机制落地

- 定义群体画像
- 定义记忆结构
- 定义动作系统
- 搭建轮次引擎
- 跑通单主线

### 阶段 2：Memoria 接入

- 接入 snapshot / branch / rollback / diff / merge
- 跑通分支对比
- 补充审计日志

### 阶段 3：Demo 表现层

- 无限画布
- 相机跟随
- 共识点动画
- 群体迁移动画
- 决策检查点
- Memoria 状态面板

### 阶段 4：案例打磨

- 选定主场景
- 打磨群体画像
- 打磨策略分叉
- 打磨结局和对比脚本

---

## 22. 最终一句话定义

这个系统不是“舆情预测器”，而是：

`一个基于 Agent + Memoria 的社会舆论事件策略沙盘：让不同认知群体带着各自记忆对事件连续反应、相互影响，并在关键节点由用户注入公司策略，从而形成可分叉、可回溯、可审计、可比较的多步演化路径。`

---

## 23. 为什么有了这份设计稿之后就可以开始实操

因为关键的不确定性已经被定义清楚：

1. `Agent 表示什么`
2. `记忆存什么`
3. `每一轮怎么推进`
4. `公司何时介入`
5. `什么叫共识点`
6. `什么叫收敛`
7. `Demo 画面怎么组织`
8. `代码模块怎么拆`

接下来可以直接进入工程实现，而不需要再反复讨论产品语义。

---

## 24. 与当前目录现有 Demo 的衔接

当前目录里已经有一套可作为起点的原型：

- `demo/mock_memoria.py`
- `demo/generate_demo.py`
- `demo/dashboard_template.html`

它们可以这样迁移：

### 24.1 `demo/mock_memoria.py`

保留为 `MockMemoriaAdapter` 的基础实现，补充以下接口语义：

- `snapshot`
- `branch`
- `rollback`
- `diff`
- `merge`

### 24.2 `demo/generate_demo.py`

从“静态编排一个故事”升级为：

- 加载 `GroupProfile`
- 加载场景时间线
- 跑一轮 `pre-company phase`
- 暂停等待公司动作
- 继续 `post-company phase`
- 输出 `graph.json` 与 `state_log.json`

### 24.3 `demo/dashboard_template.html`

从“固定画面回放器”升级为：

- 真正的无限画布
- 相机跟随最新共识点
- 决策检查点交互面板
- Memoria 状态面板
- rollback / merge 镜头

### 24.4 直接可执行的第一步

推荐先做下面三件事：

1. 把当前 `SVB` 风格数据生成器替换为“食品安全事件”时间线
2. 把现有节点语义替换为“共识聚合视图”
3. 在前端加入用户可点击的公司动作面板

完成这三步后，就已经从“演示原型”进入“可交互策略沙盘”的第一版。
