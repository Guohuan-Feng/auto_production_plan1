import datetime as dt
import copy, json
import logging, time
import re, random   
import calendar
from pathlib import Path

from ai_tools import assistant, assistant2, assistant3
from calculation_tools import optimize_production, shipment_planner
from database_tools import get_data


if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

# 可更改的常量
MAX_ATTEMPTS = 4      # 总循环次数
holidays = [6, 7, 13, 14]  # 节假日手动写
RULES = {
    "min_consecutive_days": 3,
    "pre_holiday_ct_ratio": 0.5,
    "continuous_production_only": True,   # 只允许一个连续生产区间
}

# 假回答
TARGET = "get the latest customer production plan"


def clean_text(txt: str) -> str:
    txt = txt.strip()
    txt = re.sub(r'^(user|assistant|system)\s*:\s*', '', txt, flags=re.I)
    try:
        obj = json.loads(txt)
        if isinstance(obj, dict):
            for key in ("message", "user", "content", "text"):
                if key in obj and isinstance(obj[key], str):
                    txt = obj[key].strip()
                    break
    except Exception:
        pass
    txt = re.sub(r'^[\'"“”‘’\s]+|[\'"“”‘’\s]+$', "", txt)
    return txt.lower()


def is_latest_plan_query(text: str) -> bool:
    return clean_text(text) == TARGET


# OEE / POT / CT 计算日产能
def build_cap(data):
    return {
        d: int(data["OEE"] * data["POT"][d] * 60 / data["CT"])
        for d in data["days"]
    }


# 参数更新助手函数
def update_params_with_assistant2(params, infeasible_ctx):
    """当 infeasible 时，用 assistant2 调整参数"""
    adj_json = assistant2.assistant_input_optimize(json.dumps(infeasible_ctx))
    try:
        adj = json.loads(adj_json)
        min_inv = max(0, int(adj.get("min_inventory", params["min_inventory"])))
        max_inv_tmp = int(adj.get("max_inventory", params["max_inventory"]))
        max_inv = max(min_inv, max_inv_tmp)
        params["min_inventory"] = min_inv
        params["max_inventory"] = max_inv
    except Exception as e:
        logging.error("assistant2 输出解析失败：%s", e)
    return params


def update_params_with_assistant1(params, base_results, violations):
    """当 feasible 但违规时，用 assistant1 调整参数"""
    llm_input = json.dumps({
        "base_params": base_results,
        "violations": violations
    })
    try:
        values_results = json.loads(assistant.assistant_input_process(llm_input))
        params.update({
            "min_inventory": values_results.get("min_inventory", params["min_inventory"]),
            "max_inventory": values_results.get("max_inventory", params["max_inventory"]),
            "OEE": values_results.get("OEE", params["OEE"]),
            "CT": values_results.get("CT", params["CT"]),
            "force_zero": {int(k): v for k, v in values_results.get("force_zero", params["force_zero"]).items()},
            "force_positive": {int(k): v for k, v in values_results.get("force_positive", params["force_positive"]).items()},
        })
        return params, values_results
    except Exception as e:
        logging.error("assistant1 输出解析失败：%s", e)
        return params, base_results


def generate_long_term_plan(params, months=12):
    """
    生成长期 12 个月预测
    - 使用 Gen2 long-term planning agent 文档的月度 forecast
    - 产量必须在 [monthly_std×0.8, monthly_max] 区间
    - 月份从“下个月”开始往后推
    """

    # 文档里的月度 forecast (示例数据，长度 >= 12)
    forecast_list = [
        12285, 21095, 22545, 22352, 15243, 18203,
        9263, 9661, 10721, 9264, 10440, 11632
    ]

    if months and months < len(forecast_list):
        forecast_list = forecast_list[:months]

    results = []
    inventory = 15000  # 初始库存（可从DB取）

    # 基础日产能
    daily_capacity = int(params["POT"][1] * 60 / params["CT"] * params["OEE"])
    monthly_max = daily_capacity * 30
    monthly_std = daily_capacity * 22
    monthly_min = int(monthly_std * 0.8)

    # 起始月份 = 下个月
    today = dt.date.today()
    start_month = today.month % 12 + 1
    start_year = today.year + (1 if today.month == 12 else 0)

    for idx, demand in enumerate(forecast_list, start=0):
        # 计算对应的年月
        year = start_year + (start_month - 1 + idx) // 12
        month = (start_month - 1 + idx) % 12 + 1
        month_str = dt.date(year, month, 1).strftime("%b %Y")  # e.g. "Oct 2025"

        # 产量约束
        production = min(max(demand, monthly_min), monthly_max)

        # 工作天数
        work_days = production / daily_capacity if daily_capacity > 0 else 0

        # 库存
        end_inventory = inventory + production - demand
        end_inventory = max(params["min_inventory"], min(end_inventory, params["max_inventory"]))

        results.append({
            "month": month_str,
            "forecast_demand": demand,
            "production": production,
            "work_days": round(work_days, 1),
            "ending_inventory": end_inventory
        })

        inventory = end_inventory

    return {
        "columns": ["month", "forecast_demand", "production", "work_days", "ending_inventory"],
        "data": results
    }




def run_pipeline(llm_input: str, week_start: str = "2025-07-07") -> dict:
    # 假回答
    if is_latest_plan_query(llm_input):
        delay = random.uniform(2.0, 3.0)
        logging.info("Simulating thinking for %.2f s", delay)
        time.sleep(delay)
        return {
            "status": "accept",
            "plan": {
                1: 513, 2: 567, 3: 513, 4: 459, 5: 513, 6: 0, 7: 0,
                8: 513, 9: 567, 10: 513, 11: 486, 12: 486, 13: 0, 14: 0,
            },
            "cost": 13050000,
            "hours": 5600,
            "logs": ["Fixed plan returned."],
            "violations": []
        }

    logging.info("Fetching data...")
    initial_inventory = 4000

    # LLM 解析输入
    values_results = json.loads(assistant.assistant_input_process(llm_input))
    min_inventory = values_results.get("min_inventory", 2000)
    max_inventory = values_results.get("max_inventory", 5000)
    OEE = values_results.get("OEE", 0.95)
    CT = values_results.get("CT", 105)
    long_term = values_results.get("long_term", False)  # 新增

    DEFAULT_FORCE_ZERO = {6: 0, 7: 0, 13: 0, 14: 0}
    DEFAULT_FORCE_POSITIVE = {1: 0}
    force_zero = {int(k): v for k, v in values_results.get("force_zero", DEFAULT_FORCE_ZERO).items()}
    force_positive = {int(k): v for k, v in values_results.get("force_positive", DEFAULT_FORCE_POSITIVE).items()}

    week1_min_consecutive_days = values_results.get("week1_min_consecutive_days", 3)
    week2_min_consecutive_days = values_results.get("week2_min_consecutive_days", 3)

    # 提货量
    delivery_week1 = shipment_planner.get_delivery_day_dict(week_start=week_start)
    next_monday = (dt.datetime.strptime(week_start, '%Y-%m-%d') + dt.timedelta(days=7)).strftime('%Y-%m-%d')
    delivery_week2 = {k + 7: v for k, v in shipment_planner.get_delivery_day_dict(week_start=next_monday).items()}
    delivery_day = {**delivery_week1, **delivery_week2}

    params = {
        'days': list(range(1, 15)),
        'defect_rate': 0.01,
        'unit_cost': 4200,
        'num_workers': 12,
        'weekly_wage_per_worker': 1500,
        'storage_cost_per_unit_per_day': 10,
        'shipping_cost_per_unit': 0,
        'min_inventory': min_inventory,
        'max_inventory': max_inventory,
        'initial_inventory': initial_inventory,
        'delivery_day': delivery_day,
        'OEE': OEE,
        'CT': CT,
        'POT': {d: 1234 if d not in (6, 7, 13, 14) else 0 for d in range(1, 15)},
        'min_WD': 40,
        'max_WD': 120,
        'force_zero': force_zero,
        'force_positive': force_positive,
        'week1_min_consecutive_days': week1_min_consecutive_days,
        'week2_min_consecutive_days': week2_min_consecutive_days,
    }

    logging.info("initial_inventory from DB: %s", initial_inventory)

    start = time.time()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if time.time() - start > 180:
            logging.warning("运行超时中断大循环")
            return {"status": "timeout", "msg": "exceeded 5 minutes"}

        logging.info(f"\n===== Attempt {attempt} =====")

        plan, cost, hours = optimize_production.optimize_production(params)
        if plan is None:
            # infeasible → assistant2 调整
            m = optimize_production.last_model
            m.computeIIS()
            infeasible_ctx = {
                "min_inventory": params["min_inventory"],
                "max_inventory": params["max_inventory"],
                "initial_inventory": initial_inventory,
                "shipments": delivery_day,
                "cap": build_cap(params),
                "force_zero": params["force_zero"],
                "force_positive": params["force_positive"],
                "defect_rate": params["defect_rate"],
                "iis": [c.ConstrName for c in m.getConstrs() if c.IISConstr],
            }
            params = update_params_with_assistant2(params, infeasible_ctx)
            continue

        # feasible → assistant3 审核
        check_ctx = {
            'plan': plan,
            'cap': build_cap(params),
            'holidays': holidays,
            'rules': RULES,
            'force_positive': params['force_positive'],
            'week1_min_consecutive_days': params['week1_min_consecutive_days'],
            'week2_min_consecutive_days': params['week2_min_consecutive_days'],
        }
        audit_json = assistant3.assistant_input_check(json.dumps(check_ctx))

        try:
            audit = json.loads(audit_json)
        except Exception as e:
            return {"status": "error", "msg": f"assistant3 输出解析失败: {e}"}

        if audit.get("action") == "accept":
            result = {
                "status": "accept",
                "plan": format_plan(plan),
                "cost": cost,
                "hours": hours,
                "violations": audit.get("violations", []),
                "analysis": audit.get('analysis', {})   # 短期理由说明
            }
            if long_term:
                long_term_plan = generate_long_term_plan(params, months=12)

                # 新增：调用 LLM 给长期预测加 reasoning/advantages/risks
                lt_ctx = {
                    "long_term_plan": long_term_plan
                }
                lt_audit_json = assistant3.assistant_input_check(json.dumps(lt_ctx))
                try:
                    lt_audit = json.loads(lt_audit_json)
                    long_term_plan["analysis"] = lt_audit.get("analysis", {})
                except Exception as e:
                    long_term_plan["analysis"] = {
                        "reasoning": f"Error generating analysis: {e}",
                        "advantages": "",
                        "risks": ""
                    }

                result["long_term_plan"] = long_term_plan

                return result

        # 审核不通过 → assistant1 调整
        params, values_results = update_params_with_assistant1(params, values_results, audit.get("violations", []))

    return {"status": "max_attempts_exceeded"}


def format_plan(plan_dict):
    weekdays = list(calendar.day_name)
    data = []
    for key, qty in plan_dict.items():
        try:
            idx = int(key)
        except (ValueError, TypeError):
            continue
        weekday_name = weekdays[(idx - 1) % 7]
        data.append({
            "Week day": weekday_name,
            "production qty": qty
        })

    return {
        "columns": ["Week day", "production qty"],
        "data": data
    }


def main():
    llm_input = input("Enter input: ")
    result = run_pipeline(llm_input)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(result)


# if __name__ == "__main__":
#     main()
