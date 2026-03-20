from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"
TEMPLATE_PATH = ROOT / "dashboard_template.html"

STEPS = [
    {"id": "T0", "real_time": "2023-03-08 16:00", "label": "共同看到亏损公告"},
    {"id": "T1", "real_time": "2023-03-09 09:30", "label": "股价暴跌，第一次分营"},
    {"id": "T2", "real_time": "2023-03-09 15:00", "label": "VC 提款建议，第二次重组"},
    {"id": "T3", "real_time": "2023-03-09 18:00", "label": "420 亿提款请求，阵营坍缩"},
    {"id": "T4", "real_time": "2023-03-10 09:30", "label": "救助失败，新节点产生"},
    {"id": "T5", "real_time": "2023-03-10 15:00", "label": "FDIC 接管，部分回流"},
    {"id": "T6", "real_time": "2023-03-12 18:00", "label": "联合担保后，收束成两点"},
]

PERSONA_NAMES = {
    "vc_partner": "硅谷VC合伙人",
    "startup_cfo": "科技初创CFO",
    "bank_analyst": "华尔街银行分析师",
    "fed_watcher": "美联储政策观察者",
    "retail_depositor": "普通储户",
    "short_seller": "做空对冲基金经理",
    "fintech_founder": "Fintech创始人",
    "media_reporter": "科技财经记者",
    "credit_analyst": "信用评级分析师",
    "treasury_manager": "企业司库主管",
    "insurance_exec": "保险公司高管",
    "crypto_advocate": "加密货币倡导者",
}

RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
ORDER_RISK = {value: key for key, value in RISK_ORDER.items()}

CLUSTER_SCHEME = {
    "T0": {
        "origin": {
            "title": "共同起点",
            "summary": "所有人基于同一批公告、新闻与市场数据开始讨论。",
            "risk": "medium",
            "members": list(PERSONA_NAMES.keys()),
        }
    },
    "T1": {
        "run_now": {
            "title": "立刻提款派",
            "summary": "先保住现金，关系以后再修复。",
            "risk": "high",
            "members": ["vc_partner", "startup_cfo", "retail_depositor", "fintech_founder", "short_seller"],
        },
        "balance_sheet": {
            "title": "表内核查派",
            "summary": "先看资产负债表与监管处置窗口。",
            "risk": "medium",
            "members": ["bank_analyst", "credit_analyst", "treasury_manager", "insurance_exec"],
        },
        "policy_narrative": {
            "title": "政策与叙事派",
            "summary": "关注监管节奏、舆情扩散与替代叙事。",
            "risk": "medium",
            "members": ["fed_watcher", "media_reporter", "crypto_advocate"],
        },
    },
    "T2": {
        "full_withdrawal": {
            "title": "全额撤离派",
            "summary": "Founders Fund 的动作让撤离成为默认选项。",
            "risk": "critical",
            "members": ["vc_partner", "startup_cfo", "retail_depositor", "fintech_founder", "treasury_manager", "short_seller"],
        },
        "backstop_watch": {
            "title": "观察托底派",
            "summary": "仍押注监管会在系统性事件前介入。",
            "risk": "high",
            "members": ["bank_analyst", "fed_watcher", "credit_analyst", "insurance_exec"],
        },
        "narrative_contagion": {
            "title": "叙事传染派",
            "summary": "开始把事件视作信任危机与叙事裂缝。",
            "risk": "high",
            "members": ["media_reporter", "crypto_advocate"],
        },
    },
    "T3": {
        "collapse_now": {
            "title": "立即崩溃派",
            "summary": "提款速度已超过银行自救速度，认为结局已定。",
            "risk": "critical",
            "members": ["vc_partner", "startup_cfo", "retail_depositor", "fintech_founder", "short_seller", "media_reporter", "crypto_advocate"],
        },
        "forced_resolution": {
            "title": "强制接管派",
            "summary": "不再相信市场化救助，但认为监管会强制收束局面。",
            "risk": "high",
            "members": ["bank_analyst", "fed_watcher", "credit_analyst", "treasury_manager", "insurance_exec"],
        },
    },
    "T4": {
        "systemic_spillover": {
            "title": "系统性外溢派",
            "summary": "把 SVB 视作更大金融裂缝的起点。",
            "risk": "critical",
            "members": ["short_seller", "crypto_advocate", "media_reporter", "insurance_exec", "fintech_founder"],
        },
        "emergency_containment": {
            "title": "紧急收口派",
            "summary": "虽然很差，但认为监管工具仍足以画出防火线。",
            "risk": "high",
            "members": ["fed_watcher", "bank_analyst", "credit_analyst", "treasury_manager"],
        },
        "payroll_survival": {
            "title": "发薪生存派",
            "summary": "不讨论宏观，只关心这周现金和工资能否发出。",
            "risk": "high",
            "members": ["vc_partner", "startup_cfo", "retail_depositor"],
        },
    },
    "T5": {
        "backstop_working": {
            "title": "托底生效派",
            "summary": "FDIC 接管后，越来越多人转向‘虽然痛但不会系统性爆炸’。",
            "risk": "high",
            "members": ["fed_watcher", "bank_analyst", "credit_analyst", "treasury_manager", "insurance_exec", "startup_cfo", "retail_depositor"],
        },
        "contagion_not_over": {
            "title": "余震未完派",
            "summary": "接管不是结束，只是把连锁反应推迟。",
            "risk": "high",
            "members": ["vc_partner", "short_seller", "fintech_founder", "media_reporter", "crypto_advocate"],
        },
    },
    "T6": {
        "stabilization": {
            "title": "稳定回归点",
            "summary": "大多数人汇聚到‘政策已托底、系统趋稳’这个共识点。",
            "risk": "medium",
            "members": ["fed_watcher", "bank_analyst", "credit_analyst", "treasury_manager", "insurance_exec", "startup_cfo", "retail_depositor", "fintech_founder", "media_reporter"],
        },
        "aftershock": {
            "title": "尾部余震点",
            "summary": "仍有人坚持银行业的信任缺口不会立刻补上。",
            "risk": "high",
            "members": ["vc_partner", "short_seller", "crypto_advocate"],
        },
    },
}

STEP_ACTIONS = {
    "T0": ["同一组公告与新闻进入系统", "12 个角色开始围绕同一原点发言"],
    "T1": ["原点被拉开成 3 个小群体共识点", "每个点开始形成自己的短期解释框架"],
    "T2": ["有人流入已经存在的点", "新的‘叙事传染派’点被单独看见"],
    "T3": ["多个点向两个更强的共识点塌缩", "分歧不再均匀，而是开始形成主导阵营"],
    "T4": ["出现新的‘系统性外溢派’点", "发薪生存派从大阵营里单独析出"],
    "T5": ["FDIC 接管带来第一次明显回流", "一些人从悲观点迁回托底点"],
    "T6": ["大多数人并入‘稳定回归点’", "只剩少数人停留在尾部余震点"],
}

KEY_NOTES = {
    "T0": "同样的信息入口，不同的人设开始给出不同的口气与信心。",
    "T1": "第一次可视化分营出现：保命、核查、等监管。",
    "T2": "这一步是“从一个原点连到多个不同的点”最明显的时刻。",
    "T3": "不是所有点都继续长大，很多人会并到更强的点上。",
    "T4": "这里有典型的新点出现，不只是旧点之间迁移。",
    "T5": "开始出现“别的点的人跑进已存在的点”的情况。",
    "T6": "最终画面更像收束后的共识地形，而不是树状分支图。",
}


def load_batches() -> dict:
    personas: dict = {}
    for path in sorted((ROOT / "agent_batches").glob("batch*.json")):
        personas.update(json.loads(path.read_text(encoding="utf-8")))
    missing = sorted(set(PERSONA_NAMES) - set(personas))
    if missing:
        raise RuntimeError(f"Missing persona data for: {', '.join(missing)}")
    return personas


def risk_from_votes(votes: list[dict], fallback: str) -> str:
    score = round(mean(RISK_ORDER[vote["contagion_risk"]] for vote in votes))
    return ORDER_RISK.get(score, fallback)


def build_step_clusters(personas: dict, step_id: str) -> list[dict]:
    clusters = []
    for cluster_id, spec in CLUSTER_SCHEME[step_id].items():
        members = spec["members"]
        votes = [personas[agent_id][step_id] for agent_id in members]
        top_votes = sorted(
            (
                {
                    "agent_id": agent_id,
                    "agent": PERSONA_NAMES[agent_id],
                    "verdict": personas[agent_id][step_id]["verdict"],
                    "prediction": personas[agent_id][step_id]["prediction"],
                    "action": personas[agent_id][step_id]["action"],
                    "confidence": personas[agent_id][step_id]["confidence"],
                    "risk": personas[agent_id][step_id]["contagion_risk"],
                }
                for agent_id in members
            ),
            key=lambda item: item["confidence"],
            reverse=True,
        )
        clusters.append(
            {
                "id": f"{step_id}_{cluster_id}",
                "cluster_key": cluster_id,
                "title": spec["title"],
                "summary": spec["summary"],
                "risk": risk_from_votes(votes, spec["risk"]),
                "avg_confidence": round(mean(vote["confidence"] for vote in votes), 1),
                "members": members,
                "member_names": [PERSONA_NAMES[agent_id] for agent_id in members],
                "voices": top_votes,
            }
        )
    return clusters


def cluster_lookup() -> dict:
    mapping = {}
    for step_id, clusters in CLUSTER_SCHEME.items():
        for cluster_key, spec in clusters.items():
            for member in spec["members"]:
                mapping[(step_id, member)] = cluster_key
    return mapping


def build_transitions() -> dict:
    lookup = cluster_lookup()
    transitions: dict[str, list[dict]] = {}
    for prev_step, next_step in zip(STEPS, STEPS[1:]):
        flows = defaultdict(list)
        for agent_id in PERSONA_NAMES:
            source = f"{prev_step['id']}_{lookup[(prev_step['id'], agent_id)]}"
            target = f"{next_step['id']}_{lookup[(next_step['id'], agent_id)]}"
            flows[(source, target)].append(agent_id)
        transitions[next_step["id"]] = [
            {
                "from": source,
                "to": target,
                "count": len(agent_ids),
                "agents": agent_ids,
                "agent_names": [PERSONA_NAMES[agent_id] for agent_id in agent_ids],
            }
            for (source, target), agent_ids in flows.items()
        ]
    return transitions


def build_steps(personas: dict, transitions: dict) -> list[dict]:
    steps_payload = []
    for step in STEPS:
        step_id = step["id"]
        clusters = build_step_clusters(personas, step_id)
        voices = sorted(
            (
                {
                    "agent_id": agent_id,
                    "agent": PERSONA_NAMES[agent_id],
                    **personas[agent_id][step_id],
                }
                for agent_id in PERSONA_NAMES
            ),
            key=lambda item: item["confidence"],
            reverse=True,
        )
        steps_payload.append(
            {
                "id": step_id,
                "real_time": step["real_time"],
                "label": step["label"],
                "note": KEY_NOTES[step_id],
                "actions": STEP_ACTIONS[step_id],
                "clusters": clusters,
                "voices": voices,
                "transitions_in": transitions.get(step_id, []),
            }
        )
    return steps_payload


def build_scenes(steps: list[dict]) -> list[dict]:
    scenes = []
    for idx, step in enumerate(steps):
        scenes.append(
            {
                "id": f"scene_{step['id']}",
                "type": "step",
                "step_id": step["id"],
                "label": step["label"],
                "timeline_label": step["id"],
                "visible_step_count": idx + 1,
                "note": step["note"],
            }
        )

    scenes.append(
        {
            "id": "scene_rollback",
            "type": "rollback",
            "timeline_label": "RB",
            "label": "回滚到 T2 的分叉点",
            "visible_step_count": len(steps),
            "from_step_id": "T6",
            "to_step_id": "T2",
            "note": "不是重新生成总结，而是把视角从终局拉回首次显著分歧的地方。",
        }
    )
    scenes.append(
        {
            "id": "scene_merge",
            "type": "merge",
            "timeline_label": "MG",
            "label": "将胜出路径并回主线",
            "visible_step_count": len(steps),
            "winner_cluster_id": "T6_stabilization",
            "note": "主线重新点亮，最接近真实结局的群体共识被吸收成新的组织记忆。",
        }
    )
    return scenes


def build_graph() -> dict:
    personas = load_batches()
    transitions = build_transitions()
    steps = build_steps(personas, transitions)
    scenes = build_scenes(steps)
    return {
        "title": "SVB 危机回放 · 共识簇演化图",
        "subtitle": "先看见 12 个角色各自发言，再看见他们被吸入共识点，最后看见点与点之间的人群迁移、回滚和收束。",
        "steps": steps,
        "scenes": scenes,
        "finale": {
            "merge_target_label": "main 主线",
            "winner_cluster_id": "T6_stabilization",
            "rollback_to_step_id": "T2",
        },
    }


def write_dashboard(data: dict) -> Path:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = template.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))
    target = OUTPUT_DIR / "dashboard.html"
    target.write_text(html, encoding="utf-8")
    return target


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = build_graph()
    graph_path = OUTPUT_DIR / "graph.json"
    graph_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    dashboard_path = write_dashboard(data)
    print(f"generated {graph_path}")
    print(f"generated {dashboard_path}")


if __name__ == "__main__":
    main()
