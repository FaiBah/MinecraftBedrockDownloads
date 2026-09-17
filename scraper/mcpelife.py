import re,json,urllib.request
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor,as_completed
from bs4 import BeautifulSoup

BASE="https://mcpelife.com/download/"
UA={"User-Agent":"Mozilla/5.0"}
TIMEOUT=10

def req(u,h=None,method=None):
    x=UA.copy()
    if h:x.update(h)
    return urllib.request.urlopen(urllib.request.Request(u,headers=x,method=method),timeout=TIMEOUT)

def soup(u):
    with req(u) as r:return BeautifulSoup(r.read(),"html.parser")

def direct(u):
    s=soup(u)
    for a in s.find_all("a",href=True):
        if a.get_text(" ",strip=True).lower()=="download file":return urljoin(u,a["href"])
    for a in s.find_all("a",href=True):
        h=urljoin(u,a["href"])
        if ".apk" in h.lower() or ".ipa" in h.lower():return h
    raise Exception("direct URL not found")

def check(u):
    try:
        with req(u,{"Range":"bytes=0-0"}) as r:
            h=r.headers
            m=re.search(r"/(\d+)$",h.get("Content-Range",""))
            return r.status,int(m.group(1)) if m else int(h["Content-Length"]) if h.get("Content-Length") else None
    except Exception:
        try:
            with req(u,method="HEAD") as r:
                h=r.headers
                return r.status,int(h["Content-Length"]) if h.get("Content-Length") else None
        except Exception as e:
            return None,str(e)

def versions():
    s=soup(BASE)
    out={}
    for a in s.find_all("a",href=True):
        m=re.search(r"\b(Release|Beta)\s+Minecraft\s+([0-9]+(?:\.[0-9]+){1,3})\b",a.get_text(" ",strip=True),re.I)
        if m and m.group(1).lower() not in out:
            out[m.group(1).lower()]=(m.group(2),urljoin(BASE,a["href"]))
        if len(out)==2:break
    return out

def cards(u):
    return [
        (n.get_text(" ",strip=True),urljoin(u,a["href"]))
        for c in soup(u).select(".newmc-file-card")
        if (n:=c.select_one(".newmc-file-name"))
        and (a:=c.select_one("a.newmc-file-download[href]"))
    ]

def resolve(x):
    i,n,p=x
    try:
        u=direct(p)
        status,size=check(u)
        if status and 200<=status<400:
            return i,{"name":n,"url":u,"size":size,"status":"ok","http_status":status}
        return i,{"name":n,"url":u,"size":None,"status":"failed","error":f"HTTP {status}" if status else str(size),"http_status":status}
    except Exception as e:
        return i,{"name":n,"url":None,"size":None,"status":"failed","error":str(e),"http_status":None}

try:
    vs=versions()
    result={}

    with ThreadPoolExecutor(max_workers=4) as p:
        jobs={p.submit(cards,v[1]):k for k,v in vs.items()}
        for f in as_completed(jobs):
            k=jobs[f]
            try:
                result[k]={"version":vs[k][0],"files":[],"_cards":f.result()}
            except Exception as e:
                result[k]={"version":vs[k][0],"files":[],"error":str(e),"_cards":[]}

    tasks=[
        (k,i,n,u)
        for k,v in result.items()
        for i,(n,u) in enumerate(v["_cards"])
    ]
    resolved={}

    with ThreadPoolExecutor(max_workers=16) as p:
        jobs={p.submit(resolve,(i,n,u)):(k,i,n) for k,i,n,u in tasks}
        for f in as_completed(jobs):
            k,i,n=jobs[f]
            try:
                _,x=f.result()
            except Exception as e:
                x={"name":n,"url":None,"size":None,"status":"failed","error":str(e),"http_status":None}
            resolved[k,i]=x

    for k,v in result.items():
        v["files"]=[resolved[k,i] for i in range(len(v["_cards"])) if (k,i) in resolved]
        del v["_cards"]

    data={
        "source":"mcpelife",
        "release":result.get("release",{"version":None,"files":[]}),
        "beta":result.get("beta",{"version":None,"files":[]})
    }

except Exception as e:
    data={
        "source":"mcpelife",
        "error":str(e),
        "release":{"version":None,"files":[]},
        "beta":{"version":None,"files":[]}
    }

print(json.dumps(data,ensure_ascii=False,indent=2))
