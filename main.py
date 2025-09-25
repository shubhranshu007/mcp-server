import os
import base64
from github import Github, Auth
from flask import Flask, request, jsonify

# -------------------------------
# CONFIG
# -------------------------------
BRANCH = "main"
app = Flask(__name__)

# -------------------------------
# Utility Functions
# -------------------------------
def get_dockerfile_content(repo):
    """Fetch Dockerfile content from GitHub repo"""
    try:
        contents = repo.get_contents("Dockerfile", ref=BRANCH)
        dockerfile = base64.b64decode(contents.content).decode("utf-8")
        return dockerfile
    except Exception:
        return None


def detect_language(dockerfile):
    """Detect language/framework from Dockerfile"""
    lines = dockerfile.splitlines()
    for line in lines:
        line = line.strip().lower()
        if line.startswith("from"):
            if "python" in line:
                return "python"
            if "node" in line:
                return "node"
            if "openjdk" in line or "maven" in line:
                return "java-maven"
            if "gradle" in line:
                return "java-gradle"
            if "golang" in line:
                return "go"
            if "ruby" in line:
                return "ruby"
    return "unknown"


def generate_ci_yaml(language):
    """Return CI YAML string based on detected language"""
    if language == "python":
        return f"""
name: Python CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        run: pytest || echo "⚠️ No tests found"
"""
    elif language == "node":
        return f"""
name: Node.js CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      - run: npm install
      - run: npm test
"""
    elif language == "java-maven":
        return f"""
name: Java Maven CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up JDK
        uses: actions/setup-java@v3
        with:
          java-version: '17'
      - name: Build with Maven
        run: mvn -B package --file pom.xml
"""
    elif language == "java-gradle":
        return f"""
name: Java Gradle CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up JDK
        uses: actions/setup-java@v3
        with:
          java-version: '17'
      - name: Build with Gradle
        run: ./gradlew build
"""
    else:
        return f"# Unknown language: {language}"


def commit_ci_yaml(repo, language, yaml_content):
    """Commit CI YAML back to GitHub"""
    path = f".github/workflows/{language}-ci.yml"
    message = f"🤖 Auto-generated {language} CI pipeline"

    try:
        contents = repo.get_contents(path, ref=BRANCH)
        repo.update_file(contents.path, message, yaml_content, contents.sha, branch=BRANCH)
        return f"✅ Updated {path}"
    except Exception:
        repo.create_file(path, message, yaml_content, branch=BRANCH)
        return f"✅ Created {path}"


# -------------------------------
# MCP Agent Endpoints
# -------------------------------
@app.route("/", methods=["GET"])
def home():
    return "✅ MCP Server is running. Use POST /generate_ci"


@app.route("/generate_ci", methods=["POST"])
def generate_ci():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    repo_full_name = data.get("repo_full_name")
    token = data.get("github_token") or os.getenv("GITHUB_TOKEN")

    if not repo_full_name:
        return jsonify({"error": "repo_full_name is required"}), 400
    if not token:
        return jsonify({"error": "GITHUB_TOKEN is missing"}), 401

    try:
        g = Github(auth=Auth.Token(token))
        repo = g.get_repo(repo_full_name)

        dockerfile = get_dockerfile_content(repo)
        if not dockerfile:
            return jsonify({"error": "Dockerfile not found in repo"}), 404

        language = detect_language(dockerfile)
        ci_yaml = generate_ci_yaml(language)
        commit_msg = commit_ci_yaml(repo, language, ci_yaml)

        return jsonify({
            "language_detected": language,
            "commit_status": commit_msg
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


############  Browser Agent ############
@app.route("/browser_agent", methods=["GET"])
def browser_form():
    return '''
        <h2>🔧 CI Generator Agent (Browser)</h2>
        <form action="/browser_agent" method="post">
            GitHub Repo (e.g., username/repo):<br>
            <input type="text" name="repo_full_name" required><br><br>
            GitHub Token:<br>
            <input type="password" name="github_token"><br><br>
            <input type="submit" value="Generate CI">
        </form>
    '''


@app.route("/browser_agent", methods=["POST"])
def browser_agent():
    repo_full_name = request.form.get("repo_full_name")
    token = request.form.get("github_token") or os.getenv("GITHUB_TOKEN")

    if not repo_full_name:
        return "❌ Error: repo_full_name is required", 400
    if not token:
        return "❌ Error: GITHUB_TOKEN is required", 401

    try:
        g = Github(auth=Auth.Token(token))
        repo = g.get_repo(repo_full_name)

        dockerfile = get_dockerfile_content(repo)
        if not dockerfile:
            return "❌ Dockerfile not found in the repository.", 404

        language = detect_language(dockerfile)
        ci_yaml = generate_ci_yaml(language)
        commit_msg = commit_ci_yaml(repo, language, ci_yaml)

        return f"""
            ✅ CI generated successfully!<br>
            Detected Language: <b>{language}</b><br>
            Status: {commit_msg}<br><br>
            <a href="/browser_agent">Go back</a>
        """
    except Exception as e:
        return f"❌ Error: {str(e)}", 500


############  MCP Manifest ############
@app.route("/mcp.json", methods=["GET"])
def manifest():
    """Manifest for Copilot Agent"""
    return jsonify({
        "schema_version": "1",
        "name": "ci-generator",
        "description": "Generates GitHub Actions CI pipelines from Dockerfiles in repos",
        "tools": [
            {
                "name": "generate_ci",
                "description": "Generate CI workflow for a repo using its Dockerfile",
                "type": "http",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "repo_full_name": {
                            "type": "string",
                            "description": "GitHub repo full name, e.g. username/repo"
                        },
                        "github_token": {
                            "type": "string",
                            "description": "GitHub personal access token (if not using env variable)"
                        }
                    },
                    "required": ["repo_full_name"]
                },
                "url": "http://15.206.2.155:5000/generate_ci",
                "method": "POST"
            }
        ]
    })


# -------------------------------
# Run Flask agent
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
