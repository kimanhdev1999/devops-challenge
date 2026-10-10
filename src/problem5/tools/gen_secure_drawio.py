"""Generates fortified-castle.drawio: the Problem 1 architecture with security controls marked (AWS 2023 icons).

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


# ================================================================= Fortified architecture
G_ACCOUNT = GROUP + "grIcon=mxgraph.aws4.group_account;strokeColor=#CD2264;fillColor=none;fontColor=#CD2264;dashed=0;"
BADGE = {"A": "#1E8E3E", "C": "#E8710A", "R": "#5F6368"}


def badge(p, text, x, y, kind):
    """Numbered change marker: A = added, C = changed, R = accepted risk (matches SOLUTION.md)."""
    return p.v(text, x, y, 30, 18, f"rounded=1;arcSize=50;whiteSpace=wrap;html=1;fillColor={BADGE[kind]};strokeColor=none;"
               f"fontColor=#FFFFFF;fontSize=10;fontStyle=1;align=center;verticalAlign=middle;" + FONT)


a = Page("Fortified architecture", 1700, 1170)
a.v("<b style='font-size:18px'>Fortify the Castle</b><br><span style='font-size:12px;color:#545B64'>Problem 1 architecture with security built in</span>",
    20, 20, 270, 60, TEXT)

org = a.v("AWS Organization · SCPs · Control Tower guardrails", 300, 20, 1380, 1130, G_CLOUD)
prod = a.v("Prod account · exchange", 320, 60, 1040, 820, G_ACCOUNT, org)
region = a.v("Primary region (ap-southeast-1)", 340, 100, 1000, 760, G_REGION, prod)
vpc = a.v("VPC · 3 AZs · no IGW route from private subnets", 360, 140, 760, 700, G_VPC, region)
pub = a.v("Public", 380, 190, 130, 620, G_PUBLIC, vpc)
app = a.v("Private · EKS", 530, 190, 330, 620, G_PRIVATE, vpc)
data = a.v("Private · data", 880, 190, 220, 490, G_PRIVATE, vpc)
egress = a.v("Egress · inspection", 880, 700, 220, 120, G_PRIVATE, vpc)
sec = a.v("Security tooling account", 1380, 60, 280, 300, G_ACCOUNT, org)
logs = a.v("Log archive account", 1380, 380, 280, 190, G_ACCOUNT, org)
ci = a.v("Shared services / CI account", 1380, 590, 280, 290, G_ACCOUNT, org)
cust = a.v("Custody account (isolated)", 320, 900, 680, 230, G_ACCOUNT, org)
standby = a.v("Warm standby region · same controls, own KMS keys", 1020, 900, 640, 230, G_REGION, org)

# outside AWS
traders = a.v("<b>Traders</b><br>web + mobile", 40, 330, 64, 64, resource("users", "#232F3D"))
mm = a.v("<b>Market makers</b><br>API keys, mTLS", 40, 560, 64, 64, resource("users", "#232F3D"))
r53 = a.v("<b>Route 53</b><br>DNSSEC", 190, 170, 56, 56, service("route_53", NET))
shield = a.v("<b>Shield Advanced</b>", 190, 290, 56, 56, service("shield", SECURITY))
cf = a.v("<b>CloudFront</b><br>TLS 1.2+", 190, 410, 56, 56, service("cloudfront", NET))
waf = a.v("<b>AWS WAF</b><br>managed rules,<br>Bot Control", 190, 540, 56, 56, service("waf", SECURITY))

# public subnet
alb = a.v("<b>ALB</b><br>REST, mTLS<br>trust store", 415, 300, 60, 60, resource("application_load_balancer", NET), pub)
nlb = a.v("<b>NLB</b><br>WebSocket, TLS", 415, 600, 60, 60, resource("network_load_balancer", NET), pub)

# EKS
api = a.v("<b>Order API</b><br>HMAC + nonce,<br>key scopes", 570, 290, 50, 48, POD, app)
eng = a.v("<b>Matching engine</b><br>sole writer of fills", 760, 290, 50, 48, POD, app)
stby = a.v("<b>Standby engine</b>", 760, 450, 50, 48, POD, app)
rec = a.v("<b>Reconciler</b><br>fills vs ledger", 570, 450, 50, 48, POD, app)
ws = a.v("<b>WS gateway</b>", 570, 620, 50, 48, POD, app)
ledg = a.v("<b>Ledger projector</b><br>hash-chained rows", 760, 620, 50, 48, POD, app)

# data
msk = a.v("<b>MSK</b><br>IAM auth, TLS,<br>topic ACLs", 960, 260, 60, 60, service("managed_streaming_for_kafka", ANALYTICS), data)
redis = a.v("<b>ElastiCache</b><br>AUTH + TLS", 960, 420, 60, 60, service("elasticache", DB), data)
aur = a.v("<b>Aurora</b><br>IAM auth, TLS,<br>append-only ledger", 960, 560, 60, 60, service("aurora", DB), data)
nfw = a.v("<b>Network Firewall</b><br>egress allowlist", 970, 735, 44, 44, service("network_firewall", SECURITY), egress)

# regional services in prod
cog = a.v("<b>Cognito</b><br>MFA, WebAuthn,<br>step-up", 1210, 170, 56, 56, service("cognito", SECURITY), region)
kms = a.v("<b>KMS CMKs</b><br>per data class", 1210, 320, 56, 56, service("key_management_service", SECURITY), region)
sm = a.v("<b>Secrets Manager</b><br>auto-rotation", 1210, 450, 56, 56, service("secrets_manager", SECURITY), region)
s3 = a.v("<b>S3 snapshots</b><br>Object Lock", 1210, 580, 56, 56, service("s3", STORAGE), region)
ssm = a.v("<b>SSM Session Mgr</b><br>no SSH", 1210, 720, 56, 56, service("systems_manager", MGMT), region)

# security tooling account
gd = a.v("<b>GuardDuty</b><br>EKS runtime", 1410, 110, 48, 48, service("guardduty", SECURITY), sec)
sh = a.v("<b>Security Hub</b>", 1500, 110, 48, 48, service("security_hub", SECURITY), sec)
det = a.v("<b>Detective</b>", 1590, 110, 48, 48, service("detective", SECURITY), sec)
a.v("<b>Inspector</b>", 1410, 230, 48, 48, service("inspector", SECURITY), sec)
a.v("<b>Config</b><br>conformance", 1500, 230, 48, 48, service("config", MGMT), sec)
a.v("<b>SCPs</b>", 1590, 230, 48, 48, service("organizations", MGMT), sec)

# log archive account
ct = a.v("<b>Org CloudTrail</b>", 1430, 430, 48, 48, service("cloudtrail", MGMT), logs)
a.v("<b>S3 WORM</b><br>Object Lock", 1560, 430, 48, 48, service("s3", STORAGE), logs)

# CI account
ecr = a.v("<b>ECR</b><br>scanned, signed", 1430, 640, 48, 48, service("ecr", CONTAINERS), ci)
a.v("<b>Identity Center</b><br>MFA, JIT access", 1560, 640, 48, 48, service("single_sign_on", SECURITY), ci)
a.v("GitHub OIDC → short-lived deploy role<br>cosign signatures + SBOM per image<br>2-person review for prod",
    1395, 770, 255, 60, TEXT + "fontSize=11;fontColor=#232F3E;")

# custody account
wpe = a.v("<b>Withdrawal policy engine</b><br>limits, allowlist, 24 h delay", 400, 990, 50, 48, POD, cust)
appr = a.v("<b>Dual approval</b><br>above threshold", 600, 985, 56, 56, resource("users", "#232F3D"), cust)
hsm = a.v("<b>CloudHSM / MPC</b><br>hot wallet keys", 810, 985, 56, 56, service("cloudhsm", SECURITY), cust)
a.v("Warm + cold wallets offline, multi-sig. Hot wallet holds a small float.",
    340, 1090, 640, 30, TEXT + "fontSize=11;fontColor=#545B64;align=center;")

# standby region
a.v("<b>EKS</b>", 1080, 980, 48, 48, service("eks", CONTAINERS), standby)
a.v("<b>MSK</b><br>Replicator", 1220, 980, 48, 48, service("managed_streaming_for_kafka", ANALYTICS), standby)
a.v("<b>Aurora</b><br>Global DB", 1360, 980, 48, 48, service("aurora", DB), standby)
a.v("<b>S3</b><br>CRR + Object Lock", 1500, 980, 48, 48, service("s3", STORAGE), standby)

# ---- edges
a.e(traders, r53, "DNS", ASYNC, points=[(72, 198)])
a.e(traders, cf, "HTTPS / WSS", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", points=[(150, 362), (150, 438)])
a.e(shield, cf, "", "endArrow=none;" + ASYNC)
a.e(cf, waf, "", "endArrow=none;" + ASYNC)
a.e(cf, alb, "REST", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", points=[(330, 438), (330, 330)])
a.e(cf, nlb, "WSS", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", points=[(345, 438), (345, 630)])
a.e(mm, alb, "", "exitX=1;exitY=0.25;entryX=0;entryY=0.75;", points=[(315, 576), (315, 345)])
a.e(alb, api, "", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
a.e(api, redis, "hold", "exitX=1;exitY=0.75;entryX=0;entryY=0.5;", points=[(690, 326), (690, 534), (930, 534), (930, 450)])
a.e(api, msk, "produce", "exitX=0.5;exitY=0;entryX=0.5;entryY=0;", points=[(595, 240), (990, 240)])
a.e(msk, eng, "consume", "verticalAlign=bottom;exitX=0;exitY=0.333;entryX=1;entryY=0.4167;")
a.e(eng, msk, "fills (only writer)", "verticalAlign=top;exitX=1;exitY=0.833;entryX=0;entryY=0.667;")
a.e(msk, stby, "", ASYNC + "exitX=0;exitY=1;entryX=1;entryY=0.5;", points=[(928, 320), (928, 474)])
a.e(msk, ledg, "", "exitX=1;exitY=0.9;entryX=0.5;entryY=0;", points=[(1085, 314), (1085, 548), (785, 548)])
a.e(msk, ws, "", "exitX=1;exitY=0.9;entryX=0.5;entryY=0;", points=[(1085, 314), (1085, 548), (595, 548)])
a.e(ledg, aur, "", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", points=[(870, 644), (870, 590)])
a.e(ws, nlb, "", "exitX=0;exitY=0.5;entryX=1;entryY=0.5;")
a.e(rec, eng, "compare", ASYNC + "exitX=1;exitY=0.25;entryX=0;entryY=0.75;", points=[(722, 462), (722, 326)])
a.e(app, nfw, "egress", ASYNC + "exitX=0.5;exitY=1;entryX=0;entryY=0.5;", points=[(695, 830), (940, 830), (940, 757)])
a.e(msk, wpe, "withdrawal requests · PrivateLink", ASYNC + "exitX=1;exitY=0.5;entryX=0.5;entryY=0;", points=[(1110, 290), (1110, 870), (425, 870)])
a.e(wpe, appr, "")
a.e(appr, hsm, "sign")
a.e(ecr, prod, "signed images", ASYNC + "exitX=0;exitY=0.5;entryX=1;entryY=0.7366;")
a.e(prod, ct, "API + VPC logs", ASYNC + "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", points=[(1370, 470), (1370, 454)])
a.e(prod, gd, "findings", ASYNC + "exitX=1;exitY=0.06;entryX=0;entryY=0.5;", points=[(1370, 110), (1370, 134)])
a.e(region, standby, "replication", ASYNC + "exitX=0.85;exitY=1;entryX=0.3;entryY=0;")

# ---- change badges (numbers match the change table in SOLUTION.md)
badge(a, "S1", 236, 280, "A")   # Shield Advanced
badge(a, "S2", 236, 530, "C")   # WAF
badge(a, "S3", 96, 548, "A")    # market makers mTLS
badge(a, "S4", 1256, 160, "A")  # Cognito
badge(a, "S5", 612, 278, "C")   # Order API
badge(a, "S6", 815, 198, "C")   # EKS hardening (on subnet title row)
badge(a, "S7", 1012, 250, "C")  # MSK
badge(a, "S8", 1012, 410, "C")  # Redis / Aurora
badge(a, "S8", 1012, 550, "C")
badge(a, "S9", 1256, 310, "C")  # KMS / Secrets
badge(a, "S10", 1256, 570, "C") # S3 Object Lock
badge(a, "S11", 612, 440, "A")  # Reconciler + hash chain
badge(a, "S12", 1006, 726, "A") # Network Firewall
badge(a, "S13", 940, 910, "A")  # custody
badge(a, "S14", 1620, 70, "A")  # security account / SCPs
badge(a, "S15", 1620, 390, "A") # log archive
badge(a, "S16", 1620, 600, "A") # supply chain
badge(a, "S17", 1256, 710, "C") # SSM, no SSH
badge(a, "R1", 802, 280, "R")   # no service-mesh mTLS on hot path
badge(a, "R2", 1620, 910, "R")  # standby not active-active

a.v("<b>Change markers</b><br><span style='color:#1E8E3E'>■</span> S = added control<br>"
    "<span style='color:#E8710A'>■</span> S = changed from Problem 1<br><span style='color:#5F6368'>■</span> R = accepted risk"
    "<br><br>Numbers match the change table in SOLUTION.md.<br><br>Solid = request path<br>Dashed = async, logs, replication",
    20, 700, 265, 190, TEXT + "fontSize=11;rounded=1;arcSize=4;strokeColor=#D5DBDB;fillColor=#FAFAFA;spacing=10;")

out = sys.argv[1]
with open(out, "w", encoding="utf-8") as fh:
    fh.write('<mxfile host="app.diagrams.net" type="device">')
    fh.write("".join(p.xml(f"p{i}") for i, p in enumerate(PAGES, 1)))
    fh.write("</mxfile>\n")
print("wrote", out)
