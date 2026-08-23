from pathlib import Path

ALLOWED_EXTENSIONS = {'.pdf', '.md', '.markdown'}

ALLOWED_IMAGE_SUFFIX= {'.png', '.jpg', '.jpeg'}

# 用户上传文件时，文件保存的本地磁盘地址
OUT_PUT_PATH=Path(__file__).parents[2] / "out_put"

# 用户上传的原始文件保存的地址
OUT_PUT_DOCS_PATH = OUT_PUT_PATH / "docs"

# Mineru解析后的zip文件保存地址
OUT_PUT_ZIPS_PATH = OUT_PUT_PATH / "zips"

# Mineru解析后的zip文件解压后的保存地址
OUT_PUT_UNZIPS_PATH = OUT_PUT_PATH / "unzips"

# 用户上传文件最大的大小（20MB）
MAX_FILE_SIZE = 1024 * 1024 * 20

# 用户上传文件最小的大小（1kb）
MIN_FILE_SIZE = 1024

# base64图片最大的长度（5MB）
MAX_BASE64_LEN= 1024 * 1024 * 5

# 提示词文件路径
PROMPT_FILE_PATH = Path(__file__).parents[2] / "prompts"

# chunk最大长度
CHUNK_MAX_SIZE = 1000

# chunk最小长度
CHUNK_MIN_SIZE = 500

# chunk间重叠字符
CHUNK_OVERLAP = 50