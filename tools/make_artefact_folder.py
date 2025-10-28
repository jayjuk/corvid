import os
import shutil

src = r"C:\Users\me\coding\corvid"
dest = r"C:\temp\corvid"
extensions = {".py", ".json", ".bat", ".yml", ".conf"}
merged_requirements = set()
allowed_dirs = {"agentmanager", "aibroker", "airequester", "common", "messagebroker", "orchestrator", "tools"}

for root, dirs, files in os.walk(src):
    rel_path = os.path.relpath(root, src)
    
    # Skip if not in allowed directories
    if rel_path != "." and not any(rel_path.startswith(allowed_dir) for allowed_dir in allowed_dirs):
        continue
    
    dest_dir = os.path.join(dest, rel_path)
    os.makedirs(dest_dir, exist_ok=True)

    for file in files:
        # Copy specific file types
        if any(file.endswith(ext) for ext in extensions):
            src_file = os.path.join(root, file)
            dest_file = os.path.join(dest_dir, file)
            shutil.copy2(src_file, dest_file)

        # Collect requirements.txt content
        elif file.lower() == "requirements.txt":
            req_path = os.path.join(root, file)
            with open(req_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # skip empty lines or comments
                    if line and not line.startswith("#"):
                        merged_requirements.add(line)

# Write merged requirements.txt
if merged_requirements:
    os.makedirs(dest, exist_ok=True)
    merged_path = os.path.join(dest, "requirements.txt")
    with open(merged_path, "w", encoding="utf-8") as f:
        for req in sorted(merged_requirements):
            f.write(req + "\n")

print(f"Copy complete. Merged requirements written to {merged_path}")
