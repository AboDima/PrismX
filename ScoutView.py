import collections, functools, operator
import sqlite3
import json
from django.http import HttpResponse

def Accounts():
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()
    acc = []
    try:
        cur.execute("SELECT * FROM account")
        rows = cur.fetchall()
        for row in rows:
            acc.append(row[0])
        conn.close()
    except Exception:
        pass
    return acc

def View(*account):
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()

    issues = []
    healthy = []
    total = []
    response = {'services':[],'accounts':Accounts()}
    try:
        if account:
            query = f"SELECT * FROM account WHERE id={account[0]}"
        else:
            query = "SELECT * FROM account"
        cur.execute(query)
        rows = cur.fetchall()
        for row in rows:
            report = json.loads(row[1])
            for service, summary in report['last_run']['summary'].items():
                if summary['flagged_items'] == 0 and service not in str(healthy):
                    healthy.append({'service':service,'flags':summary['flagged_items']})
                else:
                    issues.append({service:int(summary['flagged_items'])})
        result = dict(functools.reduce(operator.add, 
                 map(collections.Counter, issues))) 
        for key,value in result.items():
            total.append({'service':key,'flags':value})
        total = total + healthy
        for key in total:
            response.get('services').append(key)
        return response
    except Exception:
        pass

    conn.close()
    return response

def Service(service,*account):
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()
    response = []
    response = {'services':[],'accounts':Accounts()}
    if account[0]:
        query = f"SELECT * FROM account WHERE id={account[0]}"
    else:
        query = "SELECT * FROM account"
    cur.execute(query)
    rows = cur.fetchall()
    for row in rows:
        report = json.loads(row[1])
        for k, s in report['services'][service]['findings'].items():
            if len(s['items']) > 0:
                response.get('services').append({'service':s['service'],'description':s['description'],'rationale':s['rationale'],'dashboard':s['dashboard_name'],'key':k,'account':row[0],'issues':s['items']})
    conn.close()
    # print(response)
    return response

def Report(acc_id):
    # print(acc_id)
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()
    response = {'report':'','accounts':Accounts()}
    cur.execute(f"SELECT * FROM account WHERE id={acc_id}")
    rows = cur.fetchall()
    for row in rows:
        response['report'] = row[1]
        break
    conn.close()
    return response


def ParseReport(scan):
    conn = sqlite3.connect("db.sqlite3")
    scan = scan.decode('utf-8')
    c = conn.cursor()
    c.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='account' ''')
    if c.fetchone()[0]!=1 : 
        c.execute("CREATE TABLE account(id varchar(15), report json)")
    report_str = scan
    report_json = json.loads(report_str)
    c.execute(f"select * from account where id={report_json['account_id']}")
    rows = c.fetchall()
    if len(rows) == 0:
        c.execute("insert into account values (?, ?)",    [report_json['account_id'], report_str])
        conn.commit()
        conn.close()
    else:
       query = "update account set report= ? where id = ? "
       data = (report_str, report_json['account_id'])
       c.execute(query, data)
       conn.commit()
       conn.close()
    return HttpResponse(status=201)