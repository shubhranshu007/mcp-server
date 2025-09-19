import os
import re
from flask import Flask, request, jsonify
from github import Github, Auth
from fastmcp import FastMCP

# -------------------------------
# CONFIG
# -------------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise RuntimeError("❌ GITHUB_TOKEN is required")

gh = Github(auth=Auth.Token(GITHUB_TOKEN))
mcp = FastMCP("workflow-mcp")

# -------------------------------
# Detect language
# -------------------------------
def detect_language_from_repo(repo, dockerfile_path="Dockerfile"):
    try:
        dockerfile = repo.get_contents(dockerfile_path).decoded_content.decode()
        if "python" in dockerfile.lower():
            return "python"
        elif "node" in dockerfile.lower():
            return "node"
        elif "java" in dockerfile.lower() or "openjdk" in dockerfile.lower():
            return "java"
        elif "go" in dockerfile.lower():
            return "go"
    except Exception:
        pass

    # fallback: detect from code files
    contents = repo.get_contents("")
    extensions = [f.name for f in contents]
    if any(f.endswith(".py") for f in extensions):
        return "python"
    if any(f.endswith("package.json") for f in extensions):
        return "node"
    if any(f.endswith("pom.xml") or f.endswith(".java") for f in extensions):
        return "java"
    if any(f.endswith(".go") for f in extensions):
        return "go"
    return "default"

# -------------------------------
# MCP Tool
# -------------------------------
@mcp.tool()
def copy_workflow_from_reference(current_repo_name: str, reference_repo_name: str) -> str:
    """
    Copy workflow YAML from reference repo into current repo based on detected language.
    Args:
        current_repo_name: GitHub repository (owner/repo) to update
        reference_repo_name: GitHub repository (owner/repo) containing workflow templates
    """
    current_repo = gh.get_repo(current_repo_name)
    reference_repo = gh.get_repo(reference_repo_name)

    # detect language from current repo
    language = detect_language_from_repo(current_repo)

    # pick correct workflow file from reference repo
    filename_map = {
        "python": "python-ci.yml",
        "node": "node-ci.yml",
        "java": "java-ci.yml",
        "go": "go-ci.yml",
        "default": "default-ci.yml"
    }
    workflow_file = filename_map.get(language, "default-ci.yml")

    try:
        ref_file = reference_repo.get_contents(f".github/workflows/{workflow_file}")
        workflow_content = ref_file.decoded_content.decode()
    except Exception as e:
        return f"❌ Could not find {workflow_file} in {reference_repo_name}: {e}"

    # create workflow in current repo
    try:
        current_repo.create_file(
            path=".github/workflows/ci.yml",
            message=f"Add CI workflow for {language} (copied from {reference_repo_name})",
            content=workflow_content,
            branch="main"
        )
        return f"✅ Workflow for {language} copied from {reference_repo_name} to {current_repo_name}"
    except Exception as e:
        return f"❌ Failed to add workflow: {e}"

# -------------------------------
# Run MCP
# -------------------------------
if __name__ == "__main__":
    mcp.run()
