import os
import random
import base64
import io
from typing import Tuple, Dict, Optional, List, Type
from src.plugin_system import (
    BasePlugin,
    register_plugin,
    BaseAction,
    ComponentInfo,
    ChatMode,
    ActionActivationType,
)
from src.plugin_system.base.config_types import ConfigField
from src.common.logger import get_logger
import aiohttp

logger = get_logger("send_image_plugin_sf")
class SendImageAction(BaseAction):
    """智能图片生成Action - 基于LLM生成图片"""

    # Action基本信息
    action_name = "send_image_action"
    action_description = "智能图片生成系统，支持通过硅基流动生成图片并发送"

    # 激活设置
    focus_activation_type = ActionActivationType.LLM_JUDGE  # Focus模式使用LLM判定
    normal_activation_type = ActionActivationType.KEYWORD  # Normal模式使用关键词激活

    # 关键词设置（用于Normal模式）
    activation_keywords = ["生成图片", "画图", "create image", "draw"]
    keyword_case_sensitive = False

    # LLM判定提示词（用于Focus模式）
    llm_judge_prompt = """
判定是否需要使用图片生成动作的条件：
1. 用户明确要求画图、生成图片或创作图像
2. 用户描述了想要看到的画面或场景
3. 对话中提到需要视觉化展示某些概念
4. 用户想要创意图片或艺术作品

绝对不要使用的情况：
1. 纯文字聊天和问答
2. 只是提到"图片"、"画"等词但不是要求生成
3. 谈论已存在的图片或照片
4. 技术讨论中提到绘图概念但无生成需求
5. 用户明确表示不需要图片时
"""

    mode_enable = ChatMode.ALL
    parallel_action = False

    # Action参数定义
    action_parameters = {
        "description": "要生成图片的描述，必填，输入你想要生成的图片内容",
    }

    # Action使用场景
    action_require = [
        "当用户明确要求生成图片时使用",
        "当用户描述了具体的画面或场景时使用",
        "当用户需要视觉化展示某些概念时使用",
    ]
    associated_types = ["image", "text"]
    async def execute(self) -> Tuple[bool, str]:
        api_key = self.get_config("api.sf_api_key", "default_key")
        image_size = self.get_config("api.sf_image_size", "768x1024")
        """执行智能图片生成"""
        logger.info(f"{self.log_prefix} 执行智能图片生成动作")

        # 获取参数
        description = self.action_data.get("description")

        # 参数验证
        if not description:
            error_msg = "图片描述不能为空"
            logger.error(f"{self.log_prefix} {error_msg}")
            await self.send_text("没有指定图片描述呢~")
            return False, error_msg

        # 拼接前缀
        prompt = f"best quality, absurdres, masterpiece, {description}"

        # 调用图片生成API
        try:
            # SiliconFlow API
            sf_url = "https://api.siliconflow.cn/v1/images/generations"
            sf_headers = {
                "Authorization": f"Bearer {api_key}",  # TODO: 替换为你的token
                "Content-Type": "application/json"
            }
            sf_payload = {
                "model": "Kwai-Kolors/Kolors",
                "prompt": prompt,
                "negative_prompt": "lowres, bad anatomy, bad hands, text, error, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry",
                "image_size": f"{image_size}",  # 固定分辨率
                "batch_size": 1,
                "seed": random.randint(1, 9999999999),
                "num_inference_steps": 20,
                "guidance_scale": 7.5,
            }
            logger.info(f"{self.log_prefix} 调用SiliconFlow API生成图片，参数: {sf_payload}")
            async with aiohttp.ClientSession() as session:
                async with session.post(sf_url, headers=sf_headers, json=sf_payload) as resp:
                    if resp.status != 200:
                        error_detail = await resp.text()
                        logger.error(f"SiliconFlow请求失败，状态码: {resp.status}, 返回: {error_detail}")
                        await self.send_text("图片生成失败（参数错误或服务异常）")
                        return False, f"图片生成失败（SiliconFlow请求失败: {error_detail}）"
                    result = await resp.json()
                    # 兼容url返回
                    img_url = None
                    images = result.get("data", [])
                    if images and isinstance(images, list) and len(images) > 0:
                        if "image" in images[0]:
                            img_b64 = images[0]["image"]
                            await self.send_type(type="image", data=img_b64)
                            return True, f"已生成并发送图片，prompt: {prompt}, 分辨率: 768x768"
                        if "url" in images[0]:
                            img_url = images[0]["url"]
                    elif "url" in result:
                        img_url = result["url"]
                    if img_url:
                        try:
                            async with session.get(img_url) as img_resp:
                                if img_resp.status == 200:
                                    img_bytes = await img_resp.read()
                                    base64_image_string = base64.b64encode(img_bytes).decode("utf-8")
                                    await self.send_image(base64_image_string)
                                    logger.info(f"图片已通过URL下载并转换为Base64发送")
                                    return True, f"已生成并发送图片（URL转Base64），prompt: {prompt}"
                        except Exception as e:
                            logger.error(f"图片下载或Base64转换失败: {e}")
                            await self.send_text("图片下载或处理失败")
                            return False, f"图片下载或Base64转换失败: {e}"
                    logger.error(f"SiliconFlow生成结果异常: {result}")
                    await self.send_text(f"图片生成失败（SiliconFlow生成结果异常）")
                    return False, "图片生成失败（SiliconFlow生成结果异常）"
        except Exception as e:
            logger.error(f"生成并发送图片失败: {e}")
            return False, "图片生成或发送失败"

@register_plugin
class SendImagePlugin(BasePlugin):
    # 插件基本信息
    plugin_name = "Send_Image_plugin_sf"
    plugin_description = "发送图片的插件动作，支持通过LLM生成图片并发送，兼容base64和url两种图片返回方式。"
    plugin_version = "0.5.0"
    plugin_author = "yishang"
    enable_plugin = True
    config_file_name = "config.toml"
    dependencies: list[str] = []  # 插件依赖列表
    python_dependencies: list[str] = []  # Python包依赖列表

    # 配置节描述（自动生成注释）
    config_section_descriptions = {
        "plugin": "插件启用与版本配置",
        "components": "组件启用控制",
        "api": "图片生成API相关配置",
    }

    # 配置Schema定义（自动生成config.toml）
    config_schema = {
        "plugin": {
            "enabled": ConfigField(type=bool, default=True, description="是否启用插件"),
            "config_version": ConfigField(type=str, default="1.2.1", description="配置文件版本"),
        },
        "components": {
            "enable_send_image_action": ConfigField(type=bool, default=True, description="是否启用图片生成Action"),
        },
        "api": {
            "sf_api_key": ConfigField(type=str, default="your_api_key", description="SiliconFlow API密钥（必填）", example="sk-xxxx"),
            "image_size": ConfigField(type=str, default="768x1024", description="图片分辨率，格式如768x1024"),
        },
    }

    def __init__(self, plugin_dir=None, *args, **kwargs):
        if plugin_dir is None:
            # 自动推断当前文件所在目录为插件目录
            plugin_dir = os.path.dirname(os.path.abspath(__file__))
        super().__init__(plugin_dir=plugin_dir, *args, **kwargs)

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        """返回插件包含的组件列表"""
        if self.get_config("components.enable_send_image_action", True):
            return [
                (SendImageAction.get_action_info(), SendImageAction),
            ]
        return []
