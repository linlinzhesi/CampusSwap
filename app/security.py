# ============================================================
# app/security.py
# 作用：安全相关的工具函数（密码哈希 + JWT 令牌生成/校验）
# 把安全逻辑单独抽出来，方便复用，也让代码更清晰
# ============================================================

from datetime import datetime, timedelta, timezone   # 处理时间
import jwt                                          # JWT 库
from passlib.context import CryptContext             # 密码哈希库

from . import config                                 # 导入配置

# ------------------------------------------------------------------
# 密码哈希上下文
# schemes=["bcrypt"]：使用 bcrypt 算法
# bcrypt 是「单向」哈希，无法从哈希值反推原始密码，这是安全的关键
# ------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------------------------------------------------------------------
# 函数：把明文密码变成哈希值（用于注册时存库）
# 例：hash_password("123456") 会得到一串类似 $2b$12$xxx 的乱码
# ------------------------------------------------------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# ------------------------------------------------------------------
# 函数：校验密码是否正确（用于登录时）
# 原理：把用户输入的明文，和库里存的哈希做比对，返回 True/False
# ------------------------------------------------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ------------------------------------------------------------------
# 函数：生成 JWT 令牌（用户登录成功后调用）
# 参数 user_id：要写进 token 里的用户 id
# 返回：一串 token 字符串
#
# JWT 的构成（三段，用点号连接）：header.payload.signature
#   payload 里我们放：user_id、过期时间
#   签名：用 SECRET_KEY 加密，保证 token 无法被篡改
# ------------------------------------------------------------------
def create_access_token(user_id: int) -> str:
    # 过期时间 = 现在 + 配置里的有效期
    expire = datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)

    # payload：token 里携带的数据
    payload = {
        "sub": str(user_id),     # sub 是 JWT 标准字段，放「主体」= 用户 id
        "exp": expire,           # exp 是 JWT 标准字段，放「过期时间」
    }

    # 用密钥和算法签名，生成最终 token
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.ALGORITHM)


# ------------------------------------------------------------------
# 函数：解析并校验 JWT 令牌（每次用户带 token 请求时调用）
# 返回：如果合法，返回 user_id；如果不合法/过期，抛异常
# ------------------------------------------------------------------
def decode_access_token(token: str) -> int:
    # 校验签名和过期时间，不合法会抛出异常
    payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
    # 取出 user_id 并转成整数返回
    return int(payload["sub"])
