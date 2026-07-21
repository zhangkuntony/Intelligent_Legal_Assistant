from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import re

OUT = Path("deliver_doc/output")
IMG = OUT / "images"
IMG.mkdir(exist_ok=True)
FONT = r"C:\Windows\Fonts\msyh.ttc"

def font(size, bold=False):
    return ImageFont.truetype(FONT, size, index=1 if bold else 0)

def box(draw, xy, text, fill="#EAF2F8"):
    draw.rounded_rectangle(xy, radius=12, fill=fill, outline="#2E5D8A", width=3)
    x1, y1, x2, y2 = xy
    f = font(18, True)
    bb = draw.multiline_textbbox((0, 0), text, font=f, align="center", spacing=4)
    draw.multiline_text(((x1+x2-(bb[2]-bb[0]))/2, (y1+y2-(bb[3]-bb[1]))/2), text, font=f, fill="#15334D", align="center", spacing=4)

def arrow(draw, a, b):
    draw.line((a, b), fill="#466D91", width=4)
    import math
    ang = math.atan2(b[1]-a[1], b[0]-a[0])
    for off in (2.55, -2.55):
        p=(b[0]-16*math.cos(ang+off), b[1]-16*math.sin(ang+off))
        draw.line((b,p), fill="#466D91", width=4)

def canvas(w, h, title):
    im=Image.new("RGB",(w,h),"white"); d=ImageDraw.Draw(im)
    d.text((w/2,25), title, font=font(28,True), fill="#17365D", anchor="ma")
    return im,d

def linear(name, title, labels):
    im,d=canvas(1800,500,title); x=45; y=190; width=145; gap=20
    for i,label in enumerate(labels):
        box(d,(x,y,x+width,y+105),label)
        if i: arrow(d,(x-gap+3,y+52),(x-4,y+52))
        x += width+gap
    im.save(IMG/name, dpi=(180,180))

def architecture():
    im,d=canvas(1500,980,"图 1  智能法律助手总体架构图")
    nodes=[((550,110,950,200),"Vue 3 前端界面", "#D9EAD3"),((550,270,950,360),"FastAPI API 网关", "#CFE2F3"),((120,450,420,540),"认证与 RBAC", "#FCE5CD"),((480,450,780,540),"会话 / ChatService", "#CFE2F3"),((890,450,1190,540),"文档服务", "#CFE2F3"),((1040,640,1380,730),"Loader / Cleaner / Chunker", "#D9EAD3"),((500,640,820,730),"Retriever / Promptor", "#D9EAD3"),((110,640,400,730),"LLM / MockLLM\nParser / Guardrail", "#D9EAD3"),((120,820,400,910),"PostgreSQL / pgvector", "#EADCF8"),((570,820,800,910),"Milvus", "#EADCF8"),((990,820,1220,910),"MinIO", "#EADCF8")]
    for xy,t,c in nodes: box(d,xy,t,c)
    for a,b in [((750,200),(750,270)),((750,360),(270,450)),((750,360),(630,450)),((750,360),(1040,450)),((1040,540),(1210,640)),((630,540),(660,640)),((660,730),(255,640)),((255,730),(260,820)),((660,730),(685,820)),((1210,730),(1105,820))]: arrow(d,a,b)
    im.save(IMG/"hld_architecture.png",dpi=(180,180))

def sequence():
    im,d=canvas(1550,900,"图 2  RAG 问答处理时序图")
    names=["用户","API","检索器","Promptor","LLM/Mock","Guardrail"]
    xs=[110,365,620,875,1130,1385]
    for x,n in zip(xs,names):
        box(d,(x-85,100,x+85,165),n,"#CFE2F3")
        d.line((x,165,x,820),fill="#78909C",width=2)
    msgs=[(0,1,"POST /api/chat/send"),(1,2,"search(query, Top-k=5)"),(2,1,"Evidence + citations"),(1,3,"build_prompt(query, evidence)"),(3,4,"invoke(prompt)"),(4,1,"raw JSON / text"),(1,5,"validate(payload, metrics)"),(5,1,"normalized JSON"),(1,0,"answer + citations + confidence")]
    y=230
    for s,t,label in msgs:
        arrow(d,(xs[s],y),(xs[t],y)); d.text(((xs[s]+xs[t])/2,y-28),label,font=font(15),fill="#273746",anchor="ma"); y+=65
    im.save(IMG/"hld_sequence.png",dpi=(180,180))

def deploy():
    im,d=canvas(1500,650,"图 3  部署拓扑图")
    items=[((580,110,920,195),"浏览器 Browser","#D9EAD3"),((580,260,920,345),"Nginx / 反向代理","#CFE2F3"),((580,410,920,495),"FastAPI 服务 x1..n","#CFE2F3"),((70,540,330,625),"PostgreSQL","#EADCF8"),((410,540,650,625),"Milvus","#EADCF8"),((810,540,1050,625),"MinIO","#EADCF8"),((1170,540,1450,625),"本地 Mock 模型","#EADCF8")]
    for xy,t,c in items: box(d,xy,t,c)
    for a,b in [((750,195),(750,260)),((750,345),(750,410)),((650,495),(200,540)),((700,495),(530,540)),((800,495),(930,540)),((850,495),(1310,540))]:arrow(d,a,b)
    im.save(IMG/"hld_deployment.png",dpi=(180,180))

linear("srs_e2e.png","图 1  端到端 RAG 业务流程图",["PDF/DOC\nTXT","Loader","Cleaner","Chunker","向量索引","Top-k\n检索","Prompt\nContext","LLM /\nMock","解析与\n校验","JSON /\nAPI / UI"])
architecture(); sequence(); deploy()

replacements={
 "AIA-智能法律助手-SRS-v1.0-20260716.md":["srs_e2e.png"],
 "AIA-智能法律助手-HLD-v1.0-20260716.md":["hld_architecture.png","hld_sequence.png","hld_deployment.png"],
}
pattern=re.compile(r"```mermaid\n.*?\n```",re.S)
for filename, images in replacements.items():
    path=OUT/filename; text=path.read_text(encoding="utf-8")
    iterator=iter(images)
    text=pattern.sub(lambda _: f"![可视化架构图](images/{next(iterator)})", text)
    path.write_text(text,encoding="utf-8")
