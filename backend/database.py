from sqlalchemy import create_engine, text, inspect as sa_inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# ── 数据路径（延迟读取，确保 --data-dir / 环境变量已生效） ──────────
_engine = None
_session_factory = None

def _get_db_path():
    """获取 DB_PATH，优先读取环境变量。"""
    _electron_db_path = os.getenv("DB_PATH")
    if _electron_db_path:
        return _electron_db_path, os.path.dirname(_electron_db_path)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(BASE_DIR, "allinone.db"), BASE_DIR

def _get_upload_dir_env():
    """获取 UPLOAD_DIR 环境变量，如果未设置则返回 None。"""
    return os.getenv("UPLOAD_DIR")

def get_engine():
    """获取数据库引擎（延迟初始化）。"""
    global _engine
    if _engine is None:
        db_path, _ = _get_db_path()
        db_url = f"sqlite:///{db_path}"
        # SQLite 配置（WAL 模式 + QueuePool）：
        # - WAL 模式：读写并发不互相阻塞
        # - check_same_thread: False 允许多线程访问
        # - QueuePool + pool_size=5：多连接避免 StaticPool 线程安全问题
        # - connect_args: 超时设置避免锁冲突
        _engine = create_engine(
            db_url,
            connect_args={
                "check_same_thread": False,
                "timeout": 30,  # SQLite 锁等待超时（秒）
            },
            pool_size=5,
            max_overflow=10,
        )
        # 启用 WAL 模式，允许并发读写；同时主动 checkpoint 清理历史遗留 WAL
        with _engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
            conn.commit()
    return _engine

def get_session_factory():
    """获取 SessionLocal 工厂（延迟初始化）。"""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _session_factory

Base = declarative_base()


def get_data_dir() -> str:
    """获取数据根目录（DB + uploads 的父目录）。
    Electron 桌面端：~/.allinone/
    Web 部署：backend/
    """
    _, data_dir = _get_db_path()
    return data_dir


def get_upload_dir(sub: str = "") -> str:
    """获取 uploads 目录路径。
    优先读取环境变量 UPLOAD_DIR，否则使用 {DATA_DIR}/uploads
    Args:
        sub: 可选子目录，如 "cycling"、"hiking"、"items"
    """
    env_upload = _get_upload_dir_env()
    if env_upload:
        base = env_upload
    else:
        base = os.path.join(get_data_dir(), "uploads")
    return os.path.join(base, sub) if sub else base


def get_db():
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def _auto_migrate():
    """轻量自动迁移：检测 ORM 模型中新增的列，自动 ALTER TABLE ADD COLUMN。
    仅处理 SQLite（无需复杂 migration 框架）。
    """
    import sqlite3
    db_path, _ = _get_db_path()
    if not os.path.exists(db_path):
        return  # 新库，create_all 会处理
    eng = get_engine()
    inspector = sa_inspect(eng)
    with eng.connect() as conn:
        for table_name, table_obj in Base.metadata.tables.items():
            try:
                existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
            except Exception:
                continue  # 表不存在，create_all 会处理
            for col in table_obj.columns:
                if col.name not in existing_cols:
                    col_type = col.type.compile(dialect=eng.dialect)
                    nullable = "" if col.nullable else " NOT NULL DEFAULT ''"
                    ddl = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}{nullable}"
                    try:
                        conn.execute(text(ddl))
                        conn.commit()
                        print(f"[DB] 自动迁移: {table_name}.{col.name} ({col_type})")
                    except Exception as e:
                        print(f"[DB] 自动迁移失败: {table_name}.{col.name}: {e}")


def _ensure_indexes():
    """补建 ORM 模型中声明了 index=True 但数据库中尚未创建的索引。
    SQLite 的 create_all 对已存在的表不会重建索引，需要手动检测并补建。
    """
    eng = get_engine()
    inspector = sa_inspect(eng)
    with eng.connect() as conn:
        for table_name, table_obj in Base.metadata.tables.items():
            try:
                existing_idx_names = {idx["name"] for idx in inspector.get_indexes(table_name)}
            except Exception:
                continue
            for idx in table_obj.indexes:
                if idx.name not in existing_idx_names:
                    try:
                        # 生成 CREATE INDEX DDL
                        col_names = ", ".join(c.name for c in idx.columns)
                        unique_kw = "UNIQUE " if idx.unique else ""
                        ddl = f"CREATE {unique_kw}INDEX IF NOT EXISTS {idx.name} ON {table_name} ({col_names})"
                        conn.execute(text(ddl))
                        conn.commit()
                        print(f"[DB] 补建索引: {idx.name} ON {table_name}({col_names})")
                    except Exception as e:
                        print(f"[DB] 补建索引失败: {idx.name}: {e}")


def init_db():
    from models import cycling  # noqa: F401
    from models import fund  # noqa: F401
    from models import finance  # noqa: F401
    from models import hiking  # noqa: F401
    from models import vehicle  # noqa: F401
    from models import travel  # noqa: F401
    from models import backup  # noqa: F401
    from models import auth  # noqa: F401
    from models import item  # noqa: F401
    from models import settings  # noqa: F401
    from models import running  # noqa: F401
    Base.metadata.create_all(bind=get_engine())
    # 自动迁移（补齐新增列）
    _auto_migrate()
    # 补建索引（对已存在的表补充 ORM 声明的索引）
    _ensure_indexes()
    # 初始化默认用户
    _init_default_user()
    # 初始化默认分组
    _init_default_groups()
    # 初始化基金基础库
    _init_fund_library()


def _init_default_user():
    import hashlib
    from models.auth import User
    db = get_session_factory()()
    try:
        existing = db.query(User).count()
        if existing > 0:
            return
        pwd_hash = hashlib.sha256("aio_salt_admin".encode()).hexdigest()
        admin = User(username="admin", password_hash=pwd_hash)
        db.add(admin)
        db.commit()
    finally:
        db.close()


def _init_default_groups():
    from models.fund import FundGroup
    from sqlalchemy import select
    db = get_session_factory()()
    try:
        existing = db.query(FundGroup).count()
        if existing > 0:
            return
        defaults = [
            FundGroup(id="default", name="默认分组", color="#6b7280", sort_order=0, is_default=True),
            FundGroup(id="stock", name="股票基金", color="#1a56db", sort_order=1),
            FundGroup(id="bond", name="债券基金", color="#16a34a", sort_order=2),
            FundGroup(id="gold", name="黄金商品", color="#f59e0b", sort_order=3),
        ]
        db.add_all(defaults)
        db.commit()
    finally:
        db.close()


def _init_fund_library():
    from models.fund import FundLibrary
    db = get_session_factory()()
    try:
        existing = db.query(FundLibrary).count()
        if existing > 0:
            return
        # 场外基金
        funds = [
            ("110020","易方达消费行业股票","股票型",False,"萧楠","易方达基金",256.4),
            ("161725","招商中证白酒指数(LOF)","指数型",False,"侯昊","招商基金",188.7),
            ("320007","诺安成长混合","混合型",False,"蔡嵩松","诺安基金",132.5),
            ("006228","中欧医疗健康混合A","混合型",False,"葛兰","中欧基金",312.8),
            ("270002","广发稳增债券A","债券型",False,"曾刚","广发基金",95.3),
            ("000878","广发中证传媒ETF联接A","指数型",False,"罗远航","广发基金",42.1),
            ("004997","富国天益价值混合A","股票型",False,"朱少醒","富国基金",178.6),
            ("001156","申万菱信新能源汽车混合A","股票型",False,"付娟","申万菱信",89.4),
            ("003095","中银证券新能源混合A","混合型",False,"孙晓燕","中银证券",55.2),
            ("519736","交银成长30混合A","混合型",False,"王崇","交银施罗德",220.1),
            ("420002","天弘中证食品饮料指数A","指数型",False,"谷琦彬","天弘基金",67.8),
            ("016530","汇添富中国优势精选混合","股票型",False,"劳杰男","汇添富",48.6),
            ("050025","博时标普500ETF联接A","指数型",False,"赵云阳","博时基金",76.3),
            ("519069","华夏大盘精选混合A","混合型",False,"曹名长","华夏基金",89.7),
            ("000083","汇添富稳定收益债券A","债券型",False,"张骏","汇添富",145.2),
            ("165515","信诚新兴产业混合A","混合型",False,"黄小坚","信诚基金",31.8),
            ("001718","交银趋势优先混合A","混合型",False,"杨浩","交银施罗德",186.4),
            ("519182","万家行业优选混合","混合型",False,"黄海","万家基金",92.5),
            ("008087","国泰中证全指汽车ETF联接A","指数型",False,"艾小军","国泰基金",58.9),
            ("002903","华安黄金ETF联接A","商品型",False,"翁启森","华安基金",113.5),
            ("000217","华安黄金ETF联接C","商品型",False,"许之彦","华安基金",186.2),
            ("002826","中银永利半年定期开放债券","债券型",False,"范锐","中银基金",68.4),
            ("009505","富国上海金ETF联接C","商品型",False,"王乐乐","富国基金",42.8),
            # 场内ETF - 黄金/商品类
            ("518880","华安黄金ETF","商品型",True,"许之彦","华安基金",285.3),
            ("159934","博时黄金ETF","商品型",True,"赵云阳","博时基金",198.7),
            ("159605","广发中证黄金ETF","商品型",True,"刘杰","广发基金",45.2),
            ("518680","富国上海金ETF","商品型",True,"王乐乐","富国基金",32.8),
            ("159628","华安白银ETF","商品型",True,"许之彦","华安基金",18.5),
            ("501018","南方原油ETF","商品型",True,"张其思","南方基金",58.4),
            # 场内ETF - 跨境型
            ("159941","广发纳斯达克100ETF","跨境型",True,"刘杰","广发基金",312.6),
            ("513500","博时标普500ETF","跨境型",True,"万琼","博时基金",156.8),
            ("513100","国泰纳斯达克100ETF","跨境型",True,"梁杏","国泰基金",289.4),
            ("513030","华安德国30(DAX)ETF","跨境型",True,"倪斌","华安基金",45.3),
            # 场内ETF - 股票/指数类
            ("510300","华泰柏瑞沪深300ETF","指数型",True,"柳军","华泰柏瑞",1024.8),
            ("510310","易方达沪深300ETF","指数型",True,"余海燕","易方达",623.5),
            ("510500","南方中证500ETF","指数型",True,"罗文杰","南方基金",445.2),
            ("510330","华夏沪深300ETF","指数型",True,"张弘弢","华夏基金",812.4),
            ("510230","国泰上证180金融ETF","指数型",True,"艾小军","国泰基金",65.8),
            ("510880","华泰柏瑞红利ETF","指数型",True,"李茜","华泰柏瑞",168.5),
            ("588000","华夏科创50ETF","指数型",True,"荣膺","华夏基金",398.6),
            ("588050","工银瑞信科创50ETF","指数型",True,"赵栩","工银瑞信",234.1),
            ("516160","华夏中证新能源ETF","指数型",True,"严筱娴","华夏基金",176.8),
            ("515980","华泰柏瑞中证科技ETF","指数型",True,"张弘","华泰柏瑞",89.3),
            ("512010","易方达沪深300医药ETF","指数型",True,"余海燕","易方达",145.6),
            ("512690","鹏华中证酒ETF","指数型",True,"张羽翔","鹏华基金",198.2),
            ("515050","华夏中证5G通信ETF","指数型",True,"李俊","华夏基金",156.4),
            ("159915","易方达创业板ETF","指数型",True,"刘树荣","易方达",289.7),
            ("159819","易方达中证人工智能ETF","指数型",True,"张湛","易方达",78.5),
            ("515220","国泰中证煤炭ETF","指数型",True,"谢东旭","国泰基金",45.8),
            ("159865","国联安半导体ETF","指数型",True,"黄欣","国联安",98.3),
            ("512760","国泰CES半导体ETF","指数型",True,"艾小军","国泰基金",234.5),
            ("515790","华泰柏瑞光伏产业ETF","指数型",True,"李沐阳","华泰柏瑞",89.7),
            ("159928","汇添富中证消费ETF","指数型",True,"过蓓蓓","汇添富",123.4),
            ("512100","南方中证1000ETF","指数型",True,"崔蕾","南方基金",89.6),
            ("159592","鹏华中证A50ETF","指数型",True,"余红","鹏华基金",234.5),
            ("159601","华夏中证A50ETF","指数型",True,"李俊","华夏基金",312.8),
            ("159867","国泰中证机器人ETF","指数型",True,"吴中昊","国泰基金",56.3),
            ("512480","华夏中证半导体材料设备ETF","指数型",True,"鲁亚运","华夏基金",67.4),
            # 场内ETF - 债券类
            ("511010","国泰上证5年期国债ETF","债券型",True,"艾小军","国泰基金",38.5),
            ("511260","国泰上证10年期国债ETF","债券型",True,"艾小军","国泰基金",52.3),
            ("159926","嘉实中证中期国债ETF","债券型",True,"刘宁","嘉实基金",25.8),
            ("511290","博时中证可转债及可交换债券ETF","债券型",True,"万琼","博时基金",18.2),
            ("511020","易方达中证可转债ETF","债券型",True,"林伟斌","易方达",22.6),
            ("511030","平安中证5-10年期国债ETF","债券型",True,"刘洁涵","平安基金",15.4),
            ("511000","华安国债ETF","债券型",True,"苏卿云","华安基金",12.8),
            ("511520","华宝国债ETF","债券型",True,"王慧","华宝基金",20.1),
        ]
        for code, name, ftype, is_etf, manager, company, scale in funds:
            db.add(FundLibrary(
                code=code, name=name, type=ftype, is_etf=is_etf,
                manager=manager, company=company, scale=scale
            ))
        db.commit()
    finally:
        db.close()
