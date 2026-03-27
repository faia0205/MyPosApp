import os
import ast

# まとめる対象の拡張子
TARGET_EXTENSIONS = ['.py', '.md', '.txt', '.json']
# 無視するディレクトリ名
IGNORE_DIRS = {'__pycache__', '.git', '.venv', 'venv', '.idea', '.vscode', 'backups'}

# 出力ファイル名
OUTPUT_FILE = 'all_code_structure.txt'

def read_file_content(file_path):
    """複数のエンコーディングを試してファイルを読み込む"""
    encodings = ['utf-8', 'cp932', 'shift_jis', 'iso-2022-jp']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    return f"[Error: Could not decode file with encodings: {encodings}]"

def extract_python_structure(content):
    """Pythonコードからインポート文、クラス（継承含む）、関数（引数含む）を階層を保持して抽出する"""
    try:
        tree = ast.parse(content)
        lines = []
        
        for node in tree.body:
            # インポート文の抽出
            if isinstance(node, ast.Import):
                for alias in node.names:
                    lines.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                names = [alias.name for alias in node.names]
                lines.append(f"from {module} import {', '.join(names)}")
                
            # クラス定義の抽出
            elif isinstance(node, ast.ClassDef):
                bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                base_str = f"({', '.join(bases)})" if bases else ""
                lines.append(f"\nclass {node.name}{base_str}:")
                
                # クラス内のメソッド抽出（インデント付与）
                for sub_node in node.body:
                    if isinstance(sub_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args = [a.arg for a in sub_node.args.args]
                        arg_str = ", ".join(args)
                        prefix = "async " if isinstance(sub_node, ast.AsyncFunctionDef) else ""
                        lines.append(f"    {prefix}def {sub_node.name}({arg_str}):")
                        
            # トップレベルの関数定義の抽出
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a.arg for a in node.args.args]
                arg_str = ", ".join(args)
                prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                lines.append(f"\n{prefix}def {node.name}({arg_str}):")
                
        return "\n".join(lines)
    except SyntaxError:
        return "[Error: Could not parse Python syntax]"

def merge_files(start_path):
    print(f"Start merging files from: {start_path}")
    print(f"Output file: {OUTPUT_FILE}")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk(start_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                if any(file.endswith(ext) for ext in TARGET_EXTENSIONS):
                    file_path = os.path.join(root, file)
                    
                    if file == OUTPUT_FILE:
                        continue

                    try:
                        content = read_file_content(file_path)
                        
                        # .pyの場合は構造のみ抽出、それ以外は全文
                        if file.endswith('.py'):
                            output_content = extract_python_structure(content)
                        else:
                            output_content = content
                        
                        outfile.write(f"\n{'='*50}\n")
                        outfile.write(f"File Path: {file_path}\n")
                        outfile.write(f"{'='*50}\n\n")
                        outfile.write(output_content)
                        outfile.write("\n")
                            
                    except Exception as e:
                        print(f"Skipped {file_path}: {e}")

    print(f"完了しました。出力ファイル: {OUTPUT_FILE}")

if __name__ == "__main__":
    current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'MyPosApp')
    merge_files(current_dir)