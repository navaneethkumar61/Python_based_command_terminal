import os
import shlex
import subprocess
import psutil
import shutil
from flask import Flask, request, jsonify, session, send_from_directory

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for session handling


# -------------------------
# Serve index.html from root
# -------------------------
@app.route('/')
def home():
    return send_from_directory('.', 'index.html')


# -------------------------
# Session-based current working directory
# -------------------------
def get_current_dir():
    if "cwd" not in session:
        session["cwd"] = os.getcwd()
    return session["cwd"]

def set_current_dir(path):
    session["cwd"] = os.path.abspath(path)


# -------------------------
# Command Execution Logic
# -------------------------
def execute_command(command):
    command = command.strip()
    if not command:
        return "", "No command entered"

    parts = shlex.split(command)
    cmd = parts[0]
    args = parts[1:]
    cwd = get_current_dir()

    try:
        if cmd == "pwd":
            return cwd, ""

        elif cmd == "ls":
            path = args[0] if args else cwd
            if not os.path.isabs(path):
                path = os.path.join(cwd, path)
            if not os.path.exists(path):
                return "", f"ls: cannot access '{path}': No such file or directory"
            files = os.listdir(path)
            return "\n".join(files), ""

        elif cmd == "cd":
            path = args[0] if args else os.path.expanduser("~")
            if not os.path.isabs(path):
                path = os.path.join(cwd, path)
            if not os.path.isdir(path):
                return "", f"cd: {path}: No such directory"
            set_current_dir(path)
            return f"Moved to {get_current_dir()}", ""

        elif cmd == "mkdir":
            if not args:
                return "", "mkdir: missing operand"
            path = args[0]
            if not os.path.isabs(path):
                path = os.path.join(cwd, path)
            os.makedirs(path, exist_ok=True)
            return f"Directory '{args[0]}' created", ""

        elif cmd in ["rm", "rmdir"]:
            if not args:
                return "", f"{cmd}: missing operand"
            path = args[0]
            if not os.path.isabs(path):
                path = os.path.join(cwd, path)
            if not os.path.exists(path):
                return "", f"{cmd}: cannot remove '{path}': No such file or directory"
            if os.path.isdir(path):
                shutil.rmtree(path)
                return f"Directory '{args[0]}' deleted", ""
            else:
                os.remove(path)
                return f"File '{args[0]}' deleted", ""

        elif cmd == "cpu":
            return f"CPU Usage: {psutil.cpu_percent(interval=None)}%", ""

        elif cmd == "mem":
            mem = psutil.virtual_memory()
            return f"Memory Usage: {mem.percent}%", ""

        elif cmd == "ps":
            procs = [f"{p.info['pid']}\t{p.info['name']}" for p in psutil.process_iter(['pid', 'name'])]
            return "\n".join(procs), ""

        else:
            result = subprocess.run(parts, cwd=cwd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True)
            return result.stdout.strip(), result.stderr.strip()

    except Exception as e:
        return "", str(e)



# -------------------------
# API Endpoint
# -------------------------
@app.route('/command', methods=['POST'])
def command():
    data = request.json
    cmd = data.get('command', '')
    output, error = execute_command(cmd)
    return jsonify({
        'output': output,
        'error': error,
        'cwd': get_current_dir()
    })


# -------------------------
# Run Flask
# -------------------------
if __name__ == '__main__':
    app.run(debug=True)
