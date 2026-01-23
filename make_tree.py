import os

# ==========================================
# 設定
# ==========================================
OUTPUT_FILE = 'project_structure.txt'

# 構造図に載せたくないディレクトリ（無視リスト）
IGNORE_DIRS = {
    '__pycache__', '.git', '.venv', 'venv', 'env', 
    '.idea', '.vscode', 'node_modules', 'dist', 'build',
    'migrations'
}

# 構造図に載せたくないファイル拡張子（必要であれば追加）
IGNORE_EXTENSIONS = {
    '.pyc', '.DS_Store'
}

# ==========================================
# 処理
# ==========================================

def generate_structure_file(start_path):
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"Root: {os.path.basename(start_path)}/\n")
        
        for root, dirs, files in os.walk(start_path):
            # 無視リストにあるディレクトリを除外
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            dirs.sort()
            files.sort()

            # 現在の深さを計算してインデントを作成
            level = root.replace(start_path, '').count(os.sep)
            indent = '    ' * level
            
            # ディレクトリ名の書き込み（ルート以外）
            if root != start_path:
                f.write(f"{indent}{os.path.basename(root)}/\n")
            
            # ファイル名の書き込み
            sub_indent = '    ' * (level + 1)
            for file in files:
                if not any(file.endswith(ext) for ext in IGNORE_EXTENSIONS):
                    # 出力ファイル自身は除外
                    if file == OUTPUT_FILE or file == os.path.basename(__file__):
                        continue
                    f.write(f"{sub_indent}{file}\n")

if __name__ == "__main__":
    current_dir = os.path.join(os.getcwd(), 'MyPosApp')
    generate_structure_file(current_dir)
    print(f"構造図を出力しました: {OUTPUT_FILE}")