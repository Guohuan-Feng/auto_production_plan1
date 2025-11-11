import gurobipy as gp
from gurobipy import GRB

last_model = None

def optimize_production(params):
    days = params['days']
    model = gp.Model('WeeklyProduction')
    model.Params.OutputFlag = 0

    delievery_days = list(params['delivery_day'])

    # 日产能 cap[d]
    cap = {d: int(params["OEE"] * params["POT"][d] * 60 / params["CT"]) for d in days} # 转换为整数

    print("cap[2] =", cap.get(2, None))   # 🟢 打印周二的最大产能
    print("force_positive =", params.get('force_positive', {}))  # 🟢 打印 force_positive

    # 决策变量
    x = model.addVars(days, name="prod", lb=0, ub=cap)  # 产量
    y = model.addVars(days, vtype=GRB.BINARY, name='prod_flag')     # 新增一个决策其，0=停产, 1=满产
    I = model.addVars(days, name='inv',
                      lb=params['min_inventory'],
                      ub=params['max_inventory'])  # 库存
    S = model.addVars(days, name='ship', lb=0)  # 发货量

    for d in days:
        model.addConstr(x[d] == cap[d] * y[d], name=f'cap_link_{d}')  # 二者绑定

# ==============新增的必须停产/生产的约束===========================
    force_zero = params.get('force_zero', {})     # {day: ...}
    force_positive = params.get('force_positive', {}) # {day: min_qty}

    # 必须停产：x[d] == 0
    for d in force_zero:                 # 必须停 = y[d] = 0
        if d in days:
            model.addConstr(y[d] == 0, name=f'force_zero_{d}')

    # 必须生产（最小量）：x[d] >= min_qty
    for d in force_positive:             # 必须满产 = y[d] = 1
        if d in days and d not in force_zero:
            model.addConstr(y[d] == 1, name = f'force_cap_{d}')
# ==============================================================
    # ========== 新增：工作日连续性约束 ==========
    w1 = [d for d in days if 1 <= d <= 5]
    w2 = [d for d in days if 8 <= d <= 12]

    week1_min = params.get("week1_min_consecutive_days", 0)
    week2_min = params.get("week2_min_consecutive_days", 0)

    def add_continuity_constraints(week_days, min_len, week_name):
        if min_len <= 1:  # 不要求连续，直接跳过
            return
        for d in week_days:
            if d in force_positive:  # 特例：强制产的日子可以单独存在
                continue
            # 检查当前天是否违反“最小连续天数”
            if d <= week_days[-1] - (min_len - 1):
                # 如果今天生产，那么后面至少要有 (min_len-1) 天生产
                model.addConstr(
                    y[d] <= gp.quicksum(y[d+i] for i in range(1, min_len)),
                    name=f"{week_name}_continuity_start_{d}"
                )
            # 末尾的天数要检查往前
            if d >= week_days[0] + (min_len - 1):
                model.addConstr(
                    y[d] <= gp.quicksum(y[d-i] for i in range(1, min_len)),
                    name=f"{week_name}_continuity_end_{d}"
                )

    add_continuity_constraints(w1, week1_min, "w1")
    add_continuity_constraints(w2, week2_min, "w2")
    # ===========================================================


    # 库存平衡
    for d in days:
        prev_inv = params['initial_inventory'] if d == 1 else I[d - 1]
        model.addConstr(
            I[d] == prev_inv + x[d] * (1 - params['defect_rate']) - S[d],
            name=f'inv_balance_{d}'
        )

    # 固定发货量（周二&周五）
    for d in days:
        fixed_qty = params['delivery_day'].get(d, 0)
        model.addConstr(S[d] == fixed_qty, name=f'fix_ship_{d}')

    # 库存 ≥ 发货保护 -----------------------------
    for d in params['delivery_day']:
        # 当日生产完后可用库存（出货前）
        available = (params['initial_inventory']
                     if d == 1 else I[d - 1]) \
                    + x[d] * (1 - params['defect_rate'])
        model.addConstr(S[d] <= available, name=f'ship_capacity_{d}')
        # -----------------------------------------------------

    # 每周工时约束
    weekly_hours = (gp.quicksum(x[d] * params["CT"] / 3600 for d in days)
                    / params["OEE"])  # CT是秒，转化为小时需要除3600
    model.addConstr(weekly_hours <= 2 * params["max_WD"], name="work_hours_max")
    model.addConstr(weekly_hours >= 2 * params["min_WD"], name="work_hours_min")

    # 成本最小化目标
    prod_cost = gp.quicksum(x[d] * params['unit_cost'] for d in days)
    wages = 2 * params['num_workers'] * params['weekly_wage_per_worker']
    storage = gp.quicksum(I[d] * params['storage_cost_per_unit_per_day']
                          for d in days)
    ship_cost = gp.quicksum(S[d] * params['shipping_cost_per_unit']
                            for d in delievery_days)
    model.setObjective(prod_cost + wages + storage + ship_cost, GRB.MINIMIZE)

    # 求解
    model.optimize()
    global last_model
    last_model = model

    if model.status == GRB.OPTIMAL:
        prod_plan = {d: x[d].X for d in days}
        total_cost = model.ObjVal
        return prod_plan, total_cost, weekly_hours.getValue()
    else:
        print(f"Optimization ended with status {model.status}: {model.Status}")
        return None, None, None