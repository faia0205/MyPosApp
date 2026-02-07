import os

# まとめる対象の拡張子
TARGET_EXTENSIONS = ['.py', '.md', '.txt', '.json'] # .jsonも追加推奨
# 無視するディレクトリ名
IGNORE_DIRS = {'__pycache__', '.git', '.venv', 'venv', '.idea', '.vscode', 'backups'} # dataフォルダ(DBなど)は除外推奨

# 出力ファイル名
OUTPUT_FILE = f'all_code_context.txt'

def read_file_content(file_path):
    """複数のエンコーディングを試してファイルを読み込む"""
    encodings = ['utf-8', 'cp932', 'shift_jis', 'iso-2022-jp']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    # どのエンコーディングでも読めなかった場合
    return f"[Error: Could not decode file with encodings: {encodings}]"

def merge_files(start_path):
    print(f"Start merging files from: {start_path}")
    print(f"Output file: {OUTPUT_FILE}")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        # ディレクトリを走査
        for root, dirs, files in os.walk(start_path):
            # 無視リストにあるディレクトリを除外
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                if any(file.endswith(ext) for ext in TARGET_EXTENSIONS):
                    file_path = os.path.join(root, file)
                    
                    # 出力ファイル自身は読み込まないように除外
                    if file == OUTPUT_FILE:
                        continue

                    try:
                        content = read_file_content(file_path)
                        
                        # ファイルパスの区切り書き込み
                        outfile.write(f"\n{'='*50}\n")
                        outfile.write(f"File Path: {file_path}\n")
                        outfile.write(f"{'='*50}\n\n")
                        outfile.write(content)
                        outfile.write("\n")
                        print(f"Merged: {file}")
                            
                    except Exception as e:
                        print(f"Skipped {file_path}: {e}")

    print(f"完了しました。出力ファイル: {OUTPUT_FILE}")

if __name__ == "__main__":
    # カレントディレクトリから実行
    current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'MyPosApp')
    merge_files(current_dir)