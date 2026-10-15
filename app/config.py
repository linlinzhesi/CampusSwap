# ============================================================
# app/config.py
# 作用：集中管理项目的「配置项」
# 好处：以后要改数据库密码、端口、密钥，只需要改这一个文件，
#       不用满世界找散落的配置。
# ============================================================

# 数据库连接地址（SQLAlchemy 的 URL 格式）
# 格式：mysql+pymysql://用户名:密码@地址:端口/数据库名?charset=utf8mb4
# 说明：
#   - 用户名 root、密码 123456 是你本地 MySQL 的账号
#   - localhost:3306 是本地 MySQL 的地址和端口
#   - campus_market 是我们项目的数据库名（会自动创建，见 database.py）
#   - charset=utf8mb4 让数据库支持中文和 emoji
DATABASE_URL = "mysql+pymysql://root:123456@localhost:3306/campus_market?charset=utf8mb4"

# JWT 签名密钥（SECRET_KEY）
# 作用：给登录 token 签名用。相当于「只有知道这个密钥的人，才能伪造/验证 token」
# 注意：真实项目里这个密钥要保密、要随机，绝不能提交到公开仓库。
#       这里先用一个示例字符串，方便你本地跑。
SECRET_KEY = "campus-swap-secret-key-change-me-in-production"

# JWT 使用的加密算法（HS256 是最常用的对称加密算法）
ALGORITHM = "HS256"

# token 有效期（单位：分钟）
# 这里设 30 天（43200 分钟），方便你开发调试时不用频繁重新登录
ACCESS_TOKEN_EXPIRE_MINUTES = 43200
