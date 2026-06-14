"""全局常量与默认配置。"""

from pathlib import Path

# 模型常量
GEMINI_TEXT_MODEL = "gemini-2.5-flash"
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
DOUBAO_TEXT_MODEL = "doubao-seed-2-0-lite-260428"
DOUBAO_VISION_MODEL = "doubao-seed-2-0-lite-260428"
DOUBAO_IMAGE_MODEL = "doubao-seedream-5-0-260128"

# DeepSeek defaults
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_TEXT_MODEL = "deepseek-v4-pro"
DEEPSEEK_API_KEY_FILE = Path("deepseekkey.md")

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

# 单张图 pipeline 层超时（秒）：超过此值即使 adapter 还没返回也跳过该图
# 真实生成单张 1-2 分钟，给到 5 分钟留足重试 + 网络抖动空间
DEFAULT_IMAGE_TIMEOUT_SEC = 300

# Mock 适配器模拟参数（默认 0 = 即时返回，测试友好）
# UI/进度测试时可通过环境变量调大，模拟真实生成耗时
MOCK_IMAGE_DELAY_SEC = 0.0          # 每张 mock 图的等待秒数
MOCK_TEXT_DELAY_SEC = 0.0           # 每个 mock 文本步骤的等待秒数
MOCK_IMAGE_FAIL_RATE = 0.0          # mock 图片随机失败率（0~1）
MOCK_IMAGE_HANG_RATE = 0.0          # mock 图片随机卡死率（0~1，卡死会触发 pipeline 超时）
