import json,re,urllib.request,urllib.parse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

BASE="https://mcpedl.org"
H={"User-Agent":"Mozilla/5.0"}
TIMEOUT=15

def get(url,data=None,range_req=False):
    h=H.copy()
    if range_req:h["Range"]="bytes=0-0"
    return urllib.request.urlopen(urllib.request.Request(url,data=data,headers=h),timeout=TIMEOUT)

def html(url,data=None):
    r=get(url,data)
    try:return r.read().decode("utf-8","ignore")
    finally:r.close()

def direct(form):
    data={x["name"]:x.get("value","") for x in form.find_all("input",attrs={"name":True})}
    url=urllib.parse.urljoin(BASE,form.get("action","/show_file.php"))
    body=html(url,urllib.parse.urlencode(data).encode())
    m=re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]+)",body)
    if not m:raise Exception("direct URL not found")
    return urllib.parse.urljoin(BASE,m.group(1))

def check(x):
    try:
        r=get(x["url"],range_req=True)
        try:
            x["http_status"]=r.status
            m=re.search(r"bytes\s+\d+-\d+/(\d+)",r.headers.get("Content-Range",""))
            if m:x["size"]=int(m.group(1))
            else:
                cl=r.headers.get("Content-Length")
                x["size"]=int(cl) if cl else None
            x["status"]="ok"
        finally:r.close()
    except Exception as e:
        x["status"]="failed"
        x["error"]=str(e)
        x["http_status"]=None
    return x

home=BeautifulSoup(html(f"{BASE}/downloading/"),"html.parser")
selected={}
forms=[f for f in home.find_all("form") if re.search(r"/getfile/\d+",f.get("action",""))]

for f in forms[:2]:
    pu=f.find("input",attrs={"name":"post_url"})
    pt=f.find("input",attrs={"name":"post_title"})
    if not pu or not pt:continue
    page=urllib.parse.urljoin(BASE,pu.get("value",""))
    title=pt.get("value","")
    m=re.search(r"(\d+(?:\.\d+)+)",title) or re.search(r"(\d+(?:\.\d+)+)",page)
    if not m:continue
    v=m.group(1)
    kind="release" if len(v.split("."))==2 else "beta"
    selected[kind]=(kind,v,page)

def scrape(job):
    kind,v,page=job
    try:
        s=BeautifulSoup(html(page),"html.parser")
        forms=[]
        seen=set()

        for tr in s.find_all("tr"):
            form=tr.find("form",action=re.compile(r"/show_file\.php"))
            if not form:continue
            fid=form.find("input",attrs={"name":"file_id"})
            if not fid:continue
            fid=fid.get("value","")
            if not fid or fid in seen:continue
            seen.add(fid)
            cells=tr.find_all(["td","th"])
            name=cells[0].get_text(" ",strip=True) if cells else f"Download {v}"
            forms.append((name,form))

        def resolve(item):
            name,form=item
            try:
                return {"name":name,"url":direct(form),"size":None,"status":"checking"}
            except Exception as e:
                return {"name":name,"url":None,"size":None,"status":"failed","error":str(e),"http_status":None}

        with ThreadPoolExecutor(max_workers=8) as p:
            items=list(p.map(resolve,forms))

        good=[x for x in items if x["status"]=="checking"]

        with ThreadPoolExecutor(max_workers=8) as p:
            checked=list(p.map(check,good))

        failed=[x for x in items if x["status"]=="failed"]
        return {"version":v,"files":checked+failed}
    except Exception as e:
        return {"version":v,"files":[],"status":"failed","error":str(e)}

jobs=list(selected.values())

with ThreadPoolExecutor(max_workers=2) as p:
    results=list(p.map(scrape,jobs))

out={"source":"mcpedl"}

for job,result in zip(jobs,results):
    out[job[0]]=result

for k in ("release","beta"):
    if k not in out:
        out[k]={"version":None,"files":[],"status":"failed","error":"version not found"}

print(json.dumps(out,ensure_ascii=False,indent=2))
