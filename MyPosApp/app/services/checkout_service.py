from app.repositories.transaction_repo import TransactionRepository
from app.repositories.log_repo import LogRepository
from app.models.transaction import Transaction

class CheckoutService:
    """会計確定処理を担当するサービス"""
    
    def __init__(self, trans_repo: TransactionRepository, log_repo: LogRepository):
        self.trans_repo = trans_repo
        self.log_repo = log_repo

    def process_checkout(self, transaction: Transaction) -> int:
        """
        トランザクションを保存し、ログを記録する
        Returns:
            new_transaction_id (int)
        """
        # DB保存
        new_id = self.trans_repo.save(transaction)
        
        # ログ記録
        self.log_repo.add_log("info", f"会計完了: ID {new_id} ¥{transaction.total_amount}")
        
        return new_id
    
    def cancel_transaction(self, transaction_id: int) -> bool:
        """
        伝票を取消し、ログを記録する
        Returns:
            success (bool)
        """
        if self.trans_repo.delete_transaction(transaction_id):
            self.log_repo.add_log("warning", f"伝票取消: ID {transaction_id}")
            return True
        return False