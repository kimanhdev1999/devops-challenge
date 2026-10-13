"""Renders docs/pipeline-backend.png and docs/pipeline-frontend.png for SOLUTION.md.

    pip install diagrams   # also needs Graphviz (brew install graphviz)
    python pipeline_diagram.py

The library ships no AWS DevOps Agent icon yet, so the DevOps Guru icon stands in for it.
"""

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import ECR, EC2AutoScaling
from diagrams.aws.devtools import Codeartifact, Codebuild
from diagrams.aws.management import AmazonDevopsGuru, SystemsManagerRunCommand
from diagrams.aws.network import ALB, CloudFront
from diagrams.aws.storage import S3
from diagrams.aws.general import User
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.vcs import Github

GRAPH = {"fontname": "Helvetica", "fontsize": "22", "pad": "0.4", "nodesep": "0.7", "ranksep": "1.0"}
NODE = {"fontname": "Helvetica", "fontsize": "12"}
EDGE = {"fontname": "Helvetica", "fontsize": "11"}

FAIL = {"color": "firebrick", "style": "dashed", "fontcolor": "firebrick"}
CACHE = {"color": "darkorange", "style": "dotted", "fontcolor": "darkorange"}
GATE = {"color": "darkgreen", "fontcolor": "darkgreen"}


def source():
    repo = Github("GitHub repo\nPR · push to main")
    actions = GithubActions("GitHub Actions\nOIDC · environments")
    repo >> actions
    return actions


def dependency_cache():
    with Cluster("Dependency cache (CI account)"):
        npm = Codeartifact("CodeArtifact\nnpm ← npmjs")
        base = ECR("ECR pull-through\nnode:22-alpine")
    return npm, base


with Diagram("Backend → EC2", filename="pipeline-backend", show=False, direction="LR",
             graph_attr=GRAPH, node_attr=NODE, edge_attr=EDGE):
    actions = source()
    npm, base = dependency_cache()

    with Cluster("CodeBuild runners (ephemeral, one per job)"):
        gate = Codebuild("gate\nlint · test · audit\nimage build · Trivy")
        build = Codebuild("build once\nSBOM · provenance\nscan pushed digest")
    registry = ECR("ECR\nbackend:<sha> (immutable)")

    with Cluster("staging"):
        stg_ssm = SystemsManagerRunCommand("SSM Run Command\none instance at a time")
        stg_asg = EC2AutoScaling("EC2 ASG\ndrain · swap · /healthz")
        stg_alb = ALB("ALB\nsmoke test")
    approval = User("required\nreviewer")
    with Cluster("production"):
        prod_ssm = SystemsManagerRunCommand("SSM Run Command\none instance at a time")
        prod_asg = EC2AutoScaling("EC2 ASG\ndrain · swap · /healthz")
        prod_alb = ALB("ALB\nsmoke test")

    agent = AmazonDevopsGuru("AWS DevOps Agent\nroot-cause investigation")

    actions >> gate >> Edge(label="main only", **GATE) >> build >> Edge(label="push digest") >> registry
    npm >> Edge(xlabel="npm ci", **CACHE) >> gate
    npm >> Edge(**CACHE) >> build
    base >> Edge(xlabel="FROM", **CACHE) >> gate
    base >> Edge(**CACHE) >> build
    registry >> Edge(label="same digest") >> stg_ssm >> stg_asg >> Edge(label="re-register") >> stg_alb
    stg_alb >> Edge(label="smoke OK", **GATE) >> approval >> prod_ssm >> prod_asg >> Edge(label="re-register") >> prod_alb
    build >> Edge(**FAIL) >> agent
    stg_alb >> Edge(**FAIL) >> agent
    prod_alb >> Edge(label="any failure\n(after auto-rollback)", **FAIL) >> agent


with Diagram("Frontend → S3 + CloudFront", filename="pipeline-frontend", show=False, direction="LR",
             graph_attr=GRAPH, node_attr=NODE, edge_attr=EDGE):
    actions = source()
    with Cluster("Dependency cache (CI account)"):
        npm = Codeartifact("CodeArtifact\nnpm ← npmjs")

    with Cluster("CodeBuild runners (ephemeral, one per job)"):
        gate = Codebuild("gate + build once\nlint · test · audit\nartifact frontend-dist-<sha>")

    releases = S3("releases bucket\nfrontend/<sha>/ (rollback source)")

    with Cluster("staging"):
        stg_site = S3("site bucket\nassets → index.html")
        stg_cdn = CloudFront("CloudFront\ninvalidate · smoke")
    approval = User("required\nreviewer")
    with Cluster("production"):
        prod_site = S3("site bucket\nassets → index.html")
        prod_cdn = CloudFront("CloudFront\ninvalidate · smoke")

    agent = AmazonDevopsGuru("AWS DevOps Agent\nroot-cause investigation")

    actions >> gate
    npm >> Edge(label="npm ci", **CACHE) >> gate
    gate >> Edge(label="same bundle") >> stg_site >> stg_cdn
    stg_site >> Edge(xlabel="archive", style="dashed") >> releases
    stg_cdn >> Edge(label="smoke OK", **GATE) >> approval >> prod_site >> prod_cdn
    gate >> Edge(**FAIL) >> agent
    stg_cdn >> Edge(**FAIL) >> agent
    prod_cdn >> Edge(label="any failure\n(after auto-rollback)", **FAIL) >> agent
