#!/usr/bin/env python3
"""Publish a small signed-off copy of public DPO stop IDs to the X5max update feed.

Only ID, name and GPS are exported. The huge DPO API (hundreds of MB)
is downloaded by GitHub Actions, never by Android clients.
"""
import json, re, time, urllib.request, os, sys
from pathlib import Path

URL="https://dashboard.dpo.cz/api/server"
payload=json.dumps({
    "endpoint":"navi/stop/list","apiMethod":"GET","data":{},"host":None
}).encode("utf-8")
req=urllib.request.Request(URL,data=payload,method="POST",headers={
    "Content-Type":"application/json; charset=utf-8",
    "Accept":"application/json","User-Agent":"X5max-StopCatalogUpdater/1.0"
})
started=time.monotonic()
with urllib.request.urlopen(req, timeout=170) as response:
    raw=response.read(480_000_000)
print("DPO payload bytes",len(raw),"elapsed seconds",round(time.monotonic()-started,1),flush=True)
data=json.loads(raw)
if data.get("status")!="ok" or data.get("err_code")!=0:
    raise ValueError("DPO stop/list status is not OK")
stops=data.get("data",{}).get("stops",[])
if not isinstance(stops,list):
    raise ValueError("Invalid DPO stop list")
out=[]
seen=set()
for s in stops:
    sid=str(s.get("id","")).strip()
    name=str(s.get("name","")).strip()
    pos=s.get("geoPosition") or {}
    lat,lon=pos.get("lat"),pos.get("lon")
    if (not re.fullmatch(r"Z[0-9]+S[0-9]+",sid) or
        not name or sid in seen or
        not isinstance(lat,(float,int)) or not isinstance(lon,(float,int)) or
        not (48<=lat<=51 and 16<=lon<=20)):
        continue
    seen.add(sid)
    out.append({"id":sid,"name":name,"geoPosition":{"lat":lat,"lon":lon}})
if len(out)<5000:
    raise ValueError(f"Refusing partial DPO stop list: {len(out)} valid entries")
known={"Z50160","Z25444","Z25397","Z57216"}
covered={re.sub(r"S[0-9]+$","",s["id"]) for s in out}
if not known.issubset(covered):
    raise ValueError(f"Required Ostrava stops missing: {known-covered}")
out.sort(key=lambda s:s["id"])
target=Path(os.environ.get("CATALOG_DEST","/tmp/dpo-stops.json"))
target.parent.mkdir(parents=True,exist_ok=True)
target.write_text(json.dumps({"stops":out},ensure_ascii=False,separators=(",",":")),encoding="utf-8")
print("Catalog created",target,"stops",len(out),"size bytes",target.stat().st_size,"time seconds",round(time.monotonic()-started,1),flush=True)
