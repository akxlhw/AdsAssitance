"""全局常量与默认配置。"""

from pathlib import Path

# 模型常量
GEMINI_TEXT_MODEL = "gemini-2.5-flash"
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
DOUBAO_TEXT_MODEL = "doubao-seed-2-0-lite-260215"
DOUBAO_IMAGE_MODEL = "doubao-seedream-5-0-260128"

# 图像常量
REFERENCE_IMAGE_MAX_LONG_EDGE = 1536
REFERENCE_IMAGE_COUNT = 3
SCREEN_COUNT = 10
IMAGE_RATIO = (2, 3)
IMAGE_SIZE = (1200, 1800)

# 路径常量
DEFAULT_INPUT_DIR = Path("raw-material")
DEFAULT_OUTPUT_DIR = Path("result")
GEMINI_API_KEY_FILE = Path("apikey.md")
DOUBAO_API_KEY_FILE = Path("dbkey.md")
PROVIDER_CONFIG_FILE = Path("config/provider.json")

# 输出文件名
PRODUCT_REPORT_FILE = "productreport.md"
PRODUCT_TITLE_FILE = "product_title.md"
WING_KEYWORDS_FILE = "wing_keywords.md"
SELLING_POINTS_FILE = "selling_points.md"
SELLING_POINTS_JSON_FILE = "selling_points.json"
INSTAGRAM_FILE = "instagram.md"
PRODUCT_CONTEXT_FILE = "product_context.md"
IMAGE_PROMPTS_FILE = "image_prompts.json"
BEST_REFERENCE_IMAGES_FILE = "best_reference_images.json"
RUN_LOG_FILE = "run.log"

# 默认 CLI 参数
DEFAULT_MAX_RETRIES = 3
DEFAULT_REQUEST_DELAY = 2.0
DEFAULT_REQUEST_TIMEOUT_MS = 300_000
