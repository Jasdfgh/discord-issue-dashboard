"""
数据库操作封装
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import sys
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATABASE_PATH, DATA_DIR

logger = logging.getLogger("discord_dashboard.db")


def init_database():
    """初始化数据库，创建表结构"""
    # 确保 data 目录存在
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 创建 issues 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY,
            date TEXT,
            channel TEXT,
            original_source TEXT,
            category TEXT,
            issue TEXT,
            owner TEXT,
            reply_approach TEXT,
            progress TEXT,
            result TEXT,
            problem_category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 迁移: 为旧表添加 problem_category 列 (如果不存在)
    try:
        cursor.execute("ALTER TABLE issues ADD COLUMN problem_category TEXT")
    except sqlite3.OperationalError:
        pass  # 列已存在
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_date ON issues(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON issues(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_progress ON issues(progress)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_owner ON issues(owner)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_problem_category ON issues(problem_category)")
    
    # 创建同步日志表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            rows_synced INTEGER,
            status TEXT,
            message TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info(f"Database initialized: {DATABASE_PATH}")


@contextmanager
def get_connection():
    """获取数据库连接的上下文管理器"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # 返回 dict-like 对象
    try:
        yield conn
    finally:
        conn.close()


def clear_issues():
    """清空 issues 表（全量同步前调用）"""
    with get_connection() as conn:
        conn.execute("DELETE FROM issues")
        conn.commit()


def insert_issues(issues: List[Dict[str, Any]]):
    """批量插入 issues"""
    if not issues:
        return 0
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 准备 SQL
        columns = ["id", "date", "channel", "original_source", "category", 
                   "issue", "owner", "reply_approach", "progress", "result",
                   "problem_category"]
        placeholders = ", ".join(["?" for _ in columns])
        sql = f"INSERT OR REPLACE INTO issues ({', '.join(columns)}) VALUES ({placeholders})"
        
        # 批量插入
        rows = []
        for item in issues:
            row = tuple(item.get(col, "") for col in columns)
            rows.append(row)
        
        cursor.executemany(sql, rows)
        conn.commit()
        
        return len(rows)


def safe_replace_issues(issues: List[Dict[str, Any]]):
    """
    事务保护的全量替换：清空 + 插入在同一事务内
    如果插入失败，数据自动回滚，不会丢失旧数据
    """
    if not issues:
        return 0
    
    columns = ["id", "date", "channel", "original_source", "category", 
               "issue", "owner", "reply_approach", "progress", "result",
               "problem_category"]
    placeholders = ", ".join(["?" for _ in columns])
    sql = f"INSERT OR REPLACE INTO issues ({', '.join(columns)}) VALUES ({placeholders})"
    
    rows = [tuple(item.get(col, "") for col in columns) for item in issues]
    
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM issues")
        cursor.executemany(sql, rows)
        conn.commit()
        logger.info(f"Safe replace: {len(rows)} rows written in single transaction")
        return len(rows)
    except Exception as e:
        conn.rollback()
        logger.error(f"Safe replace failed, rolled back: {e}")
        raise
    finally:
        conn.close()


def log_sync(rows_synced: int, status: str, message: str = ""):
    """记录同步日志"""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sync_log (rows_synced, status, message) VALUES (?, ?, ?)",
            (rows_synced, status, message)
        )
        conn.commit()


def get_all_issues() -> List[Dict[str, Any]]:
    """获取所有 issues"""
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM issues ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]


def get_issues_count() -> int:
    """获取 issues 总数"""
    with get_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM issues")
        return cursor.fetchone()[0]


def get_last_sync() -> Optional[Dict[str, Any]]:
    """获取最后一次同步记录"""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM sync_log ORDER BY sync_time DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def search_issues(keyword: str) -> List[Dict[str, Any]]:
    """关键词搜索"""
    with get_connection() as conn:
        sql = """
            SELECT * FROM issues 
            WHERE issue LIKE ? 
               OR category LIKE ? 
               OR channel LIKE ?
               OR owner LIKE ?
               OR reply_approach LIKE ?
               OR problem_category LIKE ?
            ORDER BY id DESC
        """
        pattern = f"%{keyword}%"
        cursor = conn.execute(sql, (pattern, pattern, pattern, pattern, pattern, pattern))
        return [dict(row) for row in cursor.fetchall()]


def filter_issues(
    category: Optional[str] = None,
    progress: Optional[str] = None,
    owner: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    problem_category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """按条件筛选 issues"""
    conditions = []
    params = []
    
    if category:
        conditions.append("category = ?")
        params.append(category)
    if progress:
        conditions.append("progress = ?")
        params.append(progress)
    if owner:
        conditions.append("owner = ?")
        params.append(owner)
    if date_from:
        conditions.append("date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("date <= ?")
        params.append(date_to)
    if problem_category:
        conditions.append("problem_category = ?")
        params.append(problem_category)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    sql = f"SELECT * FROM issues WHERE {where_clause} ORDER BY id DESC"
    
    with get_connection() as conn:
        cursor = conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def get_unique_values(column: str) -> List[str]:
    """获取某列的所有唯一值（用于筛选器）"""
    with get_connection() as conn:
        cursor = conn.execute(
            f"SELECT DISTINCT {column} FROM issues WHERE {column} IS NOT NULL AND {column} != '' ORDER BY {column}"
        )
        return [row[0] for row in cursor.fetchall()]


def get_statistics() -> Dict[str, Any]:
    """获取统计数据"""
    with get_connection() as conn:
        stats = {}
        
        # 总数
        stats["total"] = conn.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
        
        # 按 progress 统计
        cursor = conn.execute(
            "SELECT progress, COUNT(*) as count FROM issues GROUP BY progress"
        )
        stats["by_progress"] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 按 category 统计 (具体问题描述)
        cursor = conn.execute(
            "SELECT category, COUNT(*) as count FROM issues GROUP BY category ORDER BY count DESC"
        )
        stats["by_category"] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 按 problem_category 统计 (问题大类)
        cursor = conn.execute(
            "SELECT problem_category, COUNT(*) as count FROM issues WHERE problem_category IS NOT NULL AND problem_category != '' GROUP BY problem_category ORDER BY count DESC"
        )
        stats["by_problem_category"] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 按 owner 统计
        cursor = conn.execute(
            "SELECT owner, COUNT(*) as count FROM issues GROUP BY owner ORDER BY count DESC"
        )
        stats["by_owner"] = {row[0]: row[1] for row in cursor.fetchall()}
        
        return stats


if __name__ == "__main__":
    # 测试
    init_database()
    print(f"数据库路径: {DATABASE_PATH}")
    print(f"Issues 数量: {get_issues_count()}")
