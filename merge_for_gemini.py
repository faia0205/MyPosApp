import os

# まとめる対象の拡張子
TARGET_EXTENSIONS = ['.py', '.md', '.txt']
# 無視するディレクトリ名
IGNORE_DIRS = {'__pycache__', '.git', '.venv', 'venv', '.idea', '.vscode'}
# 出力ファイル名
OUTPUT_FILE = 'all_code_context.txt'

def merge_files(start_path):
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        # ディレクトリを走査
        for root, dirs, files in os.walk(start_path):
            # 無視リストにあるディレクトリを除外
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                if any(file.endswith(ext) for ext in TARGET_EXTENSIONS):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            content = infile.read()
                            
                            # Geminiがファイルごとの区切りを認識しやすい形式で書き込む
                            outfile.write(f"\n{'='*50}\n")
                            outfile.write(f"File Path: {file_path}\n")
                            outfile.write(f"{'='*50}\n\n")
                            outfile.write(content)
                            outfile.write("\n")
                            
                    except Exception as e:
                        print(f"Skipped {file_path}: {e}")

    print(f"完了しました。 '{OUTPUT_FILE}' をGeminiにアップロードしてください。")

if __name__ == "__main__":
    # カレントディレクトリ以下を対象にする
    current_dir = os.path.join(os.getcwd(), 'MyPosApp')
    merge_files(current_dir)