import cx_Oracle

'''
def get_from_dali(sql):
    user = 'izy4szh'
    password = 'C30at7EO8N%)'
    host = 'SI0EXARAC05.de.bosch.com'
    port = '38000'
    service_name = 'RLDP01_CON_3.BOSCH.COM'
    tns_alias = 'REDLake_ZeusP_Consumer_DALI.world'
    dsn = cx_Oracle.makedsn(host=host, port=port, sid=tns_alias, service_name=service_name)
    connect = cx_Oracle.connect(user=user, password=password, dsn=dsn)
    cursor = connect.cursor()
    cursor.execute(sql)
    output = cursor.fetchall()
    return output
'''

def get_from_dali(sql: str):
    # 🔧 暂时不用 Oracle，直接返回一个常量库存
    # 模拟数据库查询结果，保持返回格式 [[value]]
    return [[5000]]
