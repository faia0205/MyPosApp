import logging
import os
from app.config import DATA_DIR
def setup_logger():
    os.makedirs(DATA_DIR, exist_ok=True)
    log_file = os.path.join(DATA_DIR, 'app.log')
    
    logger = logging.getLogger('MyPosApp')
    
    # 既にハンドラが登録されていればそのまま返す
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    
    # 単一ファイル・追記モード
    fh = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    fh.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    
    logger.addHandler(fh)
    return logger