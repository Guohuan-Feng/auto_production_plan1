# shipment_planner.py
import sys
from pathlib import Path
import pandas as pd

SHIP_RULE = {  # weekday: (start_offset, end_offset)
    1: (3, 6),  # Tue -> Fri ~ Mon
    4: (4, 6),  # Fri -> next Tue ~ Thu
}


def compute_shipments(df: pd.DataFrame) -> pd.DataFrame:
    """
    参数
    ----
    df : 任意粒度的 DataFrame，至少含
         ['schedule begin' (datetime), 'quantity']。

    返回
    ----
    ship_date       : actual shipping date (Timestamp)
    ship_day        : 'Tuesday' / 'Friday'
    covers          : 'YYYY-MM-DD→YYYY-MM-DD'
    shipment_qty    : int
    """
    df = df.copy()
    df['schedule begin.1'] = pd.to_datetime(df['schedule begin.1'], errors='coerce')
    if df['schedule begin.1'].isna().any():
        raise ValueError('❌ 存在无法解析为日期的 schedule begin 值！')

    daily = (df
             .groupby('schedule begin.1', as_index=False)['quantity']
             .sum()
             .set_index('schedule begin.1')
             .sort_index())

    shipments = []
    for ship_date in daily.index:
        wd = ship_date.weekday()
        if wd not in SHIP_RULE:
            continue

        start_off, end_off = SHIP_RULE[wd]
        start = ship_date + pd.Timedelta(days=start_off)
        end = ship_date + pd.Timedelta(days=end_off)

        rng = pd.date_range(start, end, freq='D')
        qty = daily.reindex(rng, fill_value=0)['quantity'].sum()

        shipments.append({
            'ship_date': ship_date,  # Timestamp 保留 dtype
            'ship_day': ship_date.strftime('%A'),
            'covers': f'{start.date()}→{end.date()}',
            'shipment_qty': int(qty)
        })

    return (pd.DataFrame(shipments)
            .sort_values('ship_date')
            .reset_index(drop=True))


# ---------------- 辅助聚合 ----------------
def shipments_to_delivery(plan: pd.DataFrame,
                          week_start: str
                          ) -> dict[int, int]:
    """
    若指定 week_start（该周周一的日期），仅统计那一周的周二/周五发货量；
    返回格式 unchanged: {2: qty_on_tue, 5: qty_on_fri}
    """
    if week_start is not None:
        week_start = pd.to_datetime(week_start).normalize()
        week_end = week_start + pd.Timedelta(days=6)
        plan = plan[(plan['ship_date'] >= week_start) &
                    (plan['ship_date'] <= week_end)]

    weekday_map = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7}
    g = (plan.groupby('ship_date')['shipment_qty']
         .sum()
         .reset_index())

    delivery: dict[int, int] = {}
    for _, row in g.iterrows():
        wd = weekday_map[row['ship_date'].weekday()]
        if wd in (2, 5):  # 只关心周二 / 周五
            delivery[wd] = delivery.get(wd, 0) + int(row['shipment_qty'])
    print(delivery)

    return delivery


# ---------------- 对外接口 ----------------
def get_delivery_day_dict(xls_name: str = 'DELFOR 6.27 Gen2.0.xlsx',
                          data_dir: str = 'data',
                          *,
                          week_start: str
                          ) -> dict[int, int]:
    src = Path(data_dir) / xls_name
    if not src.exists():
        raise FileNotFoundError(f'❌ {src} 不存在')

    df = pd.read_excel(
        src,
        usecols=['quantity', 'schedule begin.1', 'type'],
        parse_dates=['schedule begin.1']
    )
    df = df[df['type'].fillna('').str.strip().str.lower() == 'daily']

    plan = compute_shipments(df)
    return shipments_to_delivery(plan, week_start=week_start)


# ---------------- CLI 自检 ----------------
def main() -> None:
    week_start = '2025-07-07'

    try:
        delivery_dict = get_delivery_day_dict(week_start=week_start)
    except Exception as exc:
        sys.exit(str(exc))

    print('\n=== Delivery Day Dict ===')
    print(delivery_dict)

    # 若想查看完整发货计划，可取消下面两行注释：
    # plan = compute_shipments(pd.read_excel('data/DELFOR 6.27 Gen2.0.xls',
    #                      usecols=['quantity', 'schedule begin.1', 'type'],
    #                      parse_dates=['schedule begin.1']))
    # print('\n=== Shipment Plan ===\n', plan.to_string(index=False, justify="left"))


if __name__ == '__main__':
    main()
