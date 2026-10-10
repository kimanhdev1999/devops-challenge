"""Generates castle-in-the-cloud.drawio with draw.io's AWS 2023 (mxgraph.aws4) icons.

Styles are copied from jgraph/drawio Sidebar-AWS4.js and Sidebar-Kubernetes.js.
"""
import sys
from xml.sax.saxutils import quoteattr

PAGES = []
FONT = "fontFamily=Helvetica;"

# ---------------------------------------------------------------- AWS 2023 styles
PTS = ("points=[[0,0,0],[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0,0],[0,1,0],[0.25,1,0],[0.5,1,0],[0.75,1,0],"
       "[1,1,0],[0,0.25,0],[0,0.5,0],[0,0.75,0],[1,0.25,0],[1,0.5,0],[1,0.75,0]];")
NET, ANALYTICS, DB, CONTAINERS, SECURITY, STORAGE, MGMT = "#8C4FFF", "#8C4FFF", "#C925D1", "#ED7100", "#DD344C", "#7AA116", "#E7157B"
LBL = "fontSize=11;labelBackgroundColor=none;" + FONT


def service(res, color):
    """Service-level icon: coloured square (resourceIcon)."""
    return (f"sketch=0;{PTS}outlineConnect=0;fontColor=#232F3E;fillColor={color};strokeColor=#ffffff;dashed=0;"
            f"verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;aspect=fixed;"
            f"shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{res};{LBL}")


def resource(shape, color):
    """Resource-level glyph (ALB, NLB, Users)."""
    return (f"sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor={color};strokeColor=none;dashed=0;"
            f"verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;aspect=fixed;pointerEvents=1;"
            f"shape=mxgraph.aws4.{shape};{LBL}")


POD = ("aspect=fixed;sketch=0;html=1;dashed=0;whitespace=wrap;verticalLabelPosition=bottom;verticalAlign=top;"
       "fillColor=#2875E2;strokeColor=#ffffff;points=[[0.005,0.63,0],[0.1,0.2,0],[0.9,0.2,0],[0.5,0,0],[0.995,0.63,0],"
       "[0.72,0.99,0],[0.5,1,0],[0.28,0.99,0]];shape=mxgraph.kubernetes.icon2;prIcon=pod;" + LBL + "fontColor=#232F3E;")

GROUP = ("outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;fontStyle=1;container=1;pointerEvents=0;"
         "collapsible=0;recursiveResize=0;shape=mxgraph.aws4.group;verticalAlign=top;align=left;spacingLeft=30;" + FONT)
G_CLOUD = GROUP + "grIcon=mxgraph.aws4.group_aws_cloud_alt;strokeColor=#232F3E;fillColor=none;fontColor=#232F3E;dashed=0;"
G_REGION = GROUP + "grIcon=mxgraph.aws4.group_region;strokeColor=#00A4A6;fillColor=none;fontColor=#147EBA;dashed=1;"
G_VPC = GROUP + "grIcon=mxgraph.aws4.group_vpc2;strokeColor=#8C4FFF;fillColor=none;fontColor=#8C4FFF;dashed=0;"
G_PUBLIC = GROUP + "grIcon=mxgraph.aws4.group_security_group;grStroke=0;strokeColor=#7AA116;fillColor=#F2F6E8;fontColor=#248814;dashed=0;"
G_PRIVATE = GROUP + "grIcon=mxgraph.aws4.group_security_group;grStroke=0;strokeColor=#00A4A6;fillColor=#E6F6F7;fontColor=#147EBA;dashed=0;"
HILITE = ("rounded=1;arcSize=6;whiteSpace=wrap;html=1;fillColor=#FFF4E8;strokeColor=#ED7100;dashed=1;dashPattern=6 4;"
          "verticalAlign=bottom;spacingBottom=4;align=center;fontSize=10;fontColor=#ED7100;fontStyle=1;container=0;" + FONT)

EDGE = ("edgeStyle=orthogonalEdgeStyle;rounded=1;arcSize=8;html=1;endArrow=block;endFill=1;endSize=6;strokeColor=#545B64;"
        "strokeWidth=1.5;fontSize=11;fontColor=#232F3E;labelBackgroundColor=#FFFFFF;" + FONT)
ASYNC = "dashed=1;dashPattern=6 4;strokeWidth=1.25;"


class Page:
    def __init__(self, name, w, h):
        self.name, self.w, self.h, self.cells, self.n, self.abs = name, w, h, [], 0, {"1": (0, 0)}
        PAGES.append(self)

    def _id(self):
        self.n += 1
        return f"c{self.n}"

    def v(self, label, x, y, w, h, style, parent="1"):
        """x, y are absolute page coordinates; converted to parent-relative for containers."""
        i = self._id()
        px, py = self.abs[parent]
        self.abs[i] = (x, y)
        self.cells.append(
            f'<mxCell id="{i}" value={quoteattr(label)} style={quoteattr(style)} vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x - px}" y="{y - py}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return i

    def e(self, src, dst, label="", style="", points=()):
        i = self._id()
        pts = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points)
        pts = f'<Array as="points">{pts}</Array>' if pts else ""
        self.cells.append(
            f'<mxCell id="{i}" value={quoteattr(label)} style={quoteattr(EDGE + style)} edge="1" parent="1" '
            f'source="{src}" target="{dst}"><mxGeometry relative="1" as="geometry">{pts}</mxGeometry></mxCell>')

    def msg(self, x1, x2, y, label, kind="sync"):
        """Sequence message between lifeline centres at height y."""
        i = self._id()
        st = "html=1;verticalAlign=bottom;fontSize=11;labelBackgroundColor=#FFFFFF;strokeColor=#545B64;" + FONT
        st += {"sync": "endArrow=block;endFill=1;", "ret": "dashed=1;endArrow=open;endFill=0;",
               "async": "endArrow=open;endFill=0;"}[kind]
        pts, y2 = "", y
        if x1 == x2:  # self call
            st += "edgeStyle=orthogonalEdgeStyle;rounded=0;align=left;spacingLeft=8;verticalAlign=middle;"
            pts = f'<Array as="points"><mxPoint x="{x1 + 36}" y="{y}"/><mxPoint x="{x1 + 36}" y="{y + 26}"/></Array>'
            y2 = y + 26
        self.cells.append(
            f'<mxCell id="{i}" value={quoteattr(label)} style={quoteattr(st)} edge="1" parent="1">'
            f'<mxGeometry relative="1" as="geometry"><mxPoint x="{x1}" y="{y}" as="sourcePoint"/>'
            f'<mxPoint x="{x2}" y="{y2}" as="targetPoint"/>{pts}</mxGeometry></mxCell>')

    def xml(self, pid):
        return (f'<diagram id="{pid}" name={quoteattr(self.name)}><mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" '
                f'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" background="#FFFFFF" '
                f'pageWidth="{self.w}" pageHeight="{self.h}" math="0" shadow="0"><root><mxCell id="0"/>'
                f'<mxCell id="1" parent="0"/>{"".join(self.cells)}</root></mxGraphModel></diagram>')


TEXT = "text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;strokeColor=none;fillColor=none;" + FONT

# ================================================================= 1. Architecture
a = Page("1. AWS architecture", 1560, 1030)
a.v("<b style='font-size:18px'>Castle in the Cloud</b><br><span style='font-size:12px;color:#545B64'>Exchange reference architecture on AWS</span>",
    20, 20, 270, 60, TEXT)

cloud = a.v("AWS Cloud", 300, 20, 1240, 990, G_CLOUD)
region = a.v("Primary region (ap-southeast-1)", 320, 60, 1200, 740, G_REGION, cloud)
vpc = a.v("VPC · 3 Availability Zones", 340, 100, 920, 680, G_VPC, region)
pub = a.v("Public subnets", 360, 150, 160, 600, G_PUBLIC, vpc)
app = a.v("Private subnets · Amazon EKS", 540, 150, 440, 600, G_PRIVATE, vpc)
data = a.v("Private subnets · data", 1000, 150, 240, 600, G_PRIVATE, vpc)
standby_r = a.v("Warm standby region · RPO ~1 s, RTO ~15 min", 320, 830, 1200, 160, G_REGION, cloud)

# outside the cloud
traders = a.v("<b>Traders</b><br>REST + WebSocket", 50, 390, 64, 64, resource("users", "#232F3D"))
r53 = a.v("<b>Route 53</b><br>failover routing", 190, 220, 56, 56, service("route_53", NET))
cf = a.v("<b>CloudFront</b>", 190, 390, 56, 56, service("cloudfront", NET))
waf = a.v("<b>AWS WAF</b><br>rate rules per key", 190, 540, 56, 56, service("waf", SECURITY))

# public subnet
alb = a.v("<b>ALB</b><br>REST API", 410, 280, 60, 60, resource("application_load_balancer", NET), pub)
nlb = a.v("<b>NLB</b><br>WebSocket", 410, 560, 60, 60, resource("network_load_balancer", NET), pub)

# EKS
a.v("", 920, 162, 36, 36, service("eks", CONTAINERS), app)
a.v("single writer per pair", 735, 232, 160, 303, HILITE, app)
api = a.v("<b>Order API</b><br>auth, risk, balance hold", 590, 270, 50, 48, POD, app)
eng = a.v("<b>Matching engine</b><br>leader, 1 thread per pair", 790, 270, 50, 48, POD, app)
stby = a.v("<b>Standby engine</b><br>tails, publishes nothing", 790, 410, 50, 48, POD, app)
ws = a.v("<b>WebSocket gateway</b><br>fills, conflated depth", 590, 600, 50, 48, POD, app)
ledg = a.v("<b>Ledger projector</b><br>double-entry writes", 790, 600, 50, 48, POD, app)

# data
msk = a.v("<b>Amazon MSK</b><br>orders.&lt;pair&gt;, fills, depth<br>acks=all, transactions", 1090, 270, 60, 60,
          service("managed_streaming_for_kafka", ANALYTICS), data)
redis = a.v("<b>ElastiCache (Redis)</b><br>holds, rate limits", 1090, 440, 60, 60, service("elasticache", DB), data)
aur = a.v("<b>Aurora PostgreSQL</b><br>ledger, Multi-AZ", 1090, 600, 60, 60, service("aurora", DB), data)

# regional services
s3 = a.v("<b>Amazon S3</b><br>snapshots, tiered storage", 1360, 270, 60, 60, service("s3", STORAGE), region)
ath = a.v("<b>Athena</b><br>audit queries", 1360, 420, 60, 60, service("athena", ANALYTICS), region)
obs = a.v("<b>CloudWatch</b><br>AMP, Grafana, X-Ray", 1360, 560, 60, 60, service("cloudwatch_2", MGMT), region)
a.v("<b>KMS + Secrets Manager</b>", 1360, 690, 60, 60, service("key_management_service", SECURITY), region)

# standby region
a.v("<b>EKS</b><br>scaled down", 520, 880, 48, 48, service("eks", CONTAINERS), standby_r)
a.v("<b>MSK</b><br>MSK Replicator target", 760, 880, 48, 48, service("managed_streaming_for_kafka", ANALYTICS), standby_r)
a.v("<b>Aurora</b><br>Global DB secondary", 1000, 880, 48, 48, service("aurora", DB), standby_r)
a.v("<b>S3</b><br>cross-region replica", 1240, 880, 48, 48, service("s3", STORAGE), standby_r)

# edges: numbered order path
a.e(traders, r53, "DNS", ASYNC, points=[(82, 248)])
a.e(traders, cf, "① HTTPS / WSS")
a.e(cf, waf, "", "endArrow=none;" + ASYNC)
a.e(cf, alb, "REST", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", points=[(330, 418), (330, 310)])
a.e(cf, nlb, "WSS", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", points=[(345, 418), (345, 590)])
a.e(alb, api, "② place order", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
a.e(api, redis, "③ hold (Lua)", "exitX=1;exitY=0.75;entryX=0;entryY=0.5;", points=[(700, 306), (700, 550), (1060, 550), (1060, 470)])
a.e(api, msk, "④ produce, acks=all → 202", "exitX=0.5;exitY=0;entryX=0.5;entryY=0;", points=[(615, 215), (1120, 215)])
a.e(msk, eng, "⑤ consume", "verticalAlign=bottom;exitX=0;exitY=0.333;entryX=1;entryY=0.4167;")
a.e(eng, msk, "⑥ fills + offset (txn)", "verticalAlign=bottom;exitX=1;exitY=0.833;entryX=0;entryY=0.667;")
a.e(msk, stby, "tail", ASYNC + "exitX=0;exitY=1;entryX=1;entryY=0.5;", points=[(960, 330), (960, 434)])
a.e(eng, s3, "snapshots", ASYNC + "exitX=0.5;exitY=0;entryX=0.5;entryY=0;", points=[(815, 245), (1390, 245)])
a.e(msk, ws, "⑦ fills, depth", "exitX=1;exitY=0.9;entryX=0.5;entryY=0;", points=[(1215, 324), (1215, 570), (615, 570)])
a.e(msk, ledg, "", "exitX=1;exitY=0.9;entryX=0.5;entryY=0;", points=[(1215, 324), (1215, 570), (815, 570)])
a.e(ledg, aur, "⑧ ledger rows", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
a.e(ws, nlb, "⑨ push fill", "exitX=0;exitY=0.5;entryX=1;entryY=0.5;")
a.e(msk, s3, "tiered storage", ASYNC + "exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
a.e(s3, ath, "query", ASYNC + "exitX=1;exitY=0.5;entryX=1;entryY=0.5;", points=[(1450, 300), (1450, 450)])
a.e(region, standby_r, "Aurora Global DB · MSK Replicator · S3 CRR", ASYNC + "exitX=0.5;exitY=1;entryX=0.5;entryY=0;")

a.v("<b>Order path</b><br>① Trader connects via CloudFront + WAF<br>② ALB routes POST /orders to the Order API"
    "<br>③ Balance hold in Redis (atomic Lua)<br>④ Durable produce, then 202 Accepted<br>⑤ Engine consumes in offset order"
    "<br>⑥ Fills + offset committed in one transaction<br>⑦ Fills fan out to gateway and ledger"
    "<br>⑧ Double-entry rows written to Aurora<br>⑨ Fill pushed to the trader over WebSocket"
    "<br><br><span style='color:#545B64'>Solid = request path · dashed = async / replication</span>",
    20, 640, 265, 200, TEXT + "fontSize=11;rounded=1;arcSize=4;strokeColor=#D5DBDB;fillColor=#FAFAFA;spacing=10;")

# ================================================================= sequence helpers
LIFE = ("shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;container=0;collapsible=0;recursiveResize=0;"
        "outlineConnect=0;size=44;fillColor=#FFFFFF;strokeColor=#232F3E;fontStyle=1;fontSize=12;" + FONT)
LIFE_KEY = LIFE + "fillColor=#FFF4E8;strokeColor=#ED7100;"
FRAME = ("shape=umlFrame;whiteSpace=wrap;html=1;width=280;height=26;align=left;spacingLeft=8;fontSize=11;fontStyle=1;"
         "strokeColor=#545B64;fillColor=none;" + FONT)
NOTE = "shape=note;whiteSpace=wrap;html=1;size=12;fillColor=#FFF4C3;strokeColor=#B09500;fontSize=11;" + FONT


def lifelines(p, specs, x0, step, width, height):
    cx = []
    for k, (name, icon, key) in enumerate(specs):
        x = x0 + k * step
        c = x + width / 2
        p.v("", c - 20, 16, 40, 40, icon)
        p.v(name, x, 66, width, height, LIFE_KEY if key else LIFE)
        cx.append(c)
    return cx


def icon_only(style):
    return style.replace("verticalLabelPosition=bottom;", "noLabel=1;")


# ================================================================= 2. Place-order sequence
s = Page("2. Sequence - place order", 1420, 900)
T, E, A, R, K, M, W, L = lifelines(s, [
    ("Trader", icon_only(resource("users", "#232F3D")), False),
    ("CloudFront / WAF / ALB", icon_only(service("cloudfront", NET)), False),
    ("Order API", icon_only(POD), False),
    ("ElastiCache (Redis)", icon_only(service("elasticache", DB)), False),
    ("MSK orders.&lt;pair&gt;", icon_only(service("managed_streaming_for_kafka", ANALYTICS)), False),
    ("Matching engine", icon_only(POD), True),
    ("WebSocket gateway", icon_only(POD), False),
    ("Ledger projector + Aurora", icon_only(service("aurora", DB)), False),
], 20, 172, 140, 800)
s.msg(T, E, 150, "POST /orders (JWT, idempotency key)")
s.msg(E, A, 180, "forward")
s.msg(A, A, 200, "verify JWT locally,<br>validate schema + symbol")
s.msg(A, R, 260, "EVAL hold.lua: rate limit + reserve balance")
s.msg(R, A, 290, "OK (or 4xx reject, nothing produced)", "ret")
s.msg(A, K, 330, "produce OrderAccepted (acks=all)")
s.msg(K, A, 360, "ack: offset = sequence number", "ret")
s.msg(A, E, 390, "202 Accepted {orderId, seq}", "ret")
s.msg(E, T, 420, "202 Accepted  (~30-50 ms p99)", "ret")
s.v("par  [asynchronous, after the acknowledgement]", K - 30, 450, L + 100 - (K - 30), 390, FRAME)
s.msg(K, M, 500, "consume order @ offset n", "async")
s.msg(M, M, 520, "match in memory<br>price-time, &lt;1 ms")
s.msg(M, K, 590, "txn: fills + depth delta + commit offset n", "async")
s.msg(K, W, 640, "consume fills / depth", "async")
s.msg(W, T, 670, "push fill + order update (WebSocket)", "async")
s.msg(K, L, 720, "consume fills", "async")
s.msg(L, L, 740, "double-entry rows<br>in one DB transaction")
s.msg(L, R, 810, "settle / release hold", "async")

# ================================================================= 3. Failover sequence
f = Page("3. Sequence - engine failover + fencing", 1240, 820)
A_, B_, Ls, Br, S3_ = lifelines(f, [
    ("Engine A (old leader)", icon_only(POD), True),
    ("Engine B (standby)", icon_only(POD), False),
    ("Kubernetes Lease", icon_only(service("eks", CONTAINERS)), False),
    ("MSK broker", icon_only(service("managed_streaming_for_kafka", ANALYTICS)), False),
    ("S3 snapshots", icon_only(service("s3", STORAGE)), False),
], 40, 230, 160, 720)
f.msg(A_, Ls, 150, "renew lease (holder = A)")
f.msg(A_, Br, 190, "txn epoch 5: fills + commit offset")
f.msg(Br, B_, 230, "B tails the same partition, builds an identical book", "async")
f.msg(A_, S3_, 270, "snapshot book @ offset n (every N s)", "async")
f.v("A stalls: GC pause or network partition", A_ - 85, 300, 170, 44, NOTE)
f.msg(B_, Ls, 390, "lease expired: acquire (holder = B)")
f.msg(Ls, B_, 420, "granted", "ret")
f.msg(B_, Br, 460, "initTransactions(transactional.id = shard) → epoch 6")
f.msg(Br, B_, 490, "epoch 5 fenced, open transaction aborted", "ret")
f.msg(B_, B_, 510, "resume from last<br>committed offset")
f.msg(B_, Br, 580, "txn epoch 6: fills + commit offset")
f.msg(A_, Br, 630, "A wakes: produce txn epoch 5")
f.msg(Br, A_, 660, "ProducerFencedException", "ret")
f.msg(A_, A_, 680, "step down, restart<br>as standby")

out = sys.argv[1]
with open(out, "w", encoding="utf-8") as fh:
    fh.write('<mxfile host="app.diagrams.net" type="device">')
    fh.write("".join(p.xml(f"p{i}") for i, p in enumerate(PAGES, 1)))
    fh.write("</mxfile>\n")
print("wrote", out)
