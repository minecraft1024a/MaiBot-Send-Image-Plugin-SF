import os
import random
import base64
from typing import Tuple, List, Type
from src.plugin_system import (
    BasePlugin,
    register_plugin,
    BaseAction,
    ComponentInfo,
    ChatMode,
    ActionActivationType,
)
from src.plugin_system.base.config_types import ConfigField
from src.plugin_system import llm_api
from src.common.logger import get_logger
import aiohttp

logger = get_logger("send_image_plugin_sf")

class SendImageAction(BaseAction):
    """智能图片生成Action - 基于LLM生成图片"""

    # Action基本信息
    action_name = "send_image_action"
    action_description = "智能图片生成系统，支持通过硅基流动生成图片并发送"

    # 激活设置
    focus_activation_type = ActionActivationType.LLM_JUDGE
    normal_activation_type = ActionActivationType.KEYWORD

    # 关键词设置
    activation_keywords = ["生成图片", "画图", "create image", "draw"]
    keyword_case_sensitive = False

    # LLM判定提示词
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
    
    async def optimize_prompt_with_llm(self, original_prompt: str) -> str:
        """使用配置的LLM模型优化提示词（专注于二次元风格）"""
        try:
            # 1. 从配置获取默认模型名称
            default_model_name = str(self.get_config("llm.default_model", "replyer_1"))
            logger.info(f"{self.log_prefix} 配置的默认模型: {default_model_name}")
            
            # 2. 获取可用模型列表
            available_models = llm_api.get_available_models()
            logger.info(f"{self.log_prefix} 可用模型: {list(available_models.keys())}")
            
            # 3. 查找模型配置
            model_config = available_models.get(default_model_name)
            
            if not model_config:
                # 4. 如果找不到，尝试模糊匹配
                logger.warning(f"{self.log_prefix} 未找到配置的模型 '{default_model_name}'，尝试模糊匹配")
                for name, config in available_models.items():
                    if "replyer_1" in name.lower():
                        model_config = config
                        logger.info(f"{self.log_prefix} 使用替代模型: {name}")
                        break
            
            if not model_config:
                logger.warning(f"{self.log_prefix} 未找到合适的LLM模型，使用原始提示词")
                return f"anime style, {original_prompt}"

            # 5. 构建优化指令
            optimization_prompt = f"""
你是一个专业的二次元图片提示词工程师，请严格按照以下规则优化用户输入的图片描述，特别关注角色原画风：

### 优化目标：
根据用户描述生成符合角色原作风格的图片提示词，不需要过度强调画质，但要忠实还原角色特征。

### 优化规则：
1. **核心元素扩展**：
   - 角色特征：{original_prompt} - 基于此进行详细扩展
   - 服装细节：例如校服、战斗服等原作中的服装
   - 发型发色：忠实还原原作设定
   - 表情姿态：符合角色性格的典型表情和姿态
   - 场景背景：选择原作中的典型场景

2. **风格匹配**：
   - 艺术风格：忠实还原原作画风,像素风,简笔画,动漫风·等
   - 上色风格：保持原作的上色特点
   - 线条质量：符合原作的线条风格
   - 细节水平：保持原作细节水平

3. **格式要求**：
   - 使用英文短语，逗号分隔
   - 包含15-25个描述短语
   - 按以下顺序组织：风格设定 > 角色描述 > 服装细节 > 表情姿态 > 场景背景

### 画风还原示例：
输入："蔚蓝档案中的星野"
输出："Hoshino from Blue Archive, pink long hair, twin tails with black ribbons, 
blue archive school uniform, navy blazer with gold trim, white shirt, red ribbon tie, 
pleated skirt, thigh-high socks, holding a textbook, cheerful expression, slight blush, 
standing in classroom, desks and chalkboard in background, 
soft shading, clean outlines, official art style"

### 当前输入：
"{original_prompt}"

### 优化结果（只输出优化后的提示词，不要包含任何其他文字）：
"""
            # 6. 调用LLM API并处理可能的多种返回值格式
            logger.info(f"{self.log_prefix} 调用LLM优化提示词")
            
            # 调用API并处理返回值
            api_result = await llm_api.generate_with_model(
                prompt=optimization_prompt,
                model_config=model_config,
                temperature=0.7,
                max_tokens=500,
            )
            
            # 处理不同格式的返回值
            success = False
            optimized_prompt = ""
            
            if isinstance(api_result, tuple):
                # 元组格式的返回：可能是 (success, content) 或其他组合
                if len(api_result) >= 2:
                    success = api_result[0]
                    optimized_prompt = api_result[1]
                else:
                    logger.warning(f"{self.log_prefix} 返回的元组格式异常: {api_result}")
            elif isinstance(api_result, dict):
                # 字典格式的返回
                success = api_result.get("success", False)
                optimized_prompt = api_result.get("content", "")
            elif isinstance(api_result, str):
                # 直接返回字符串
                success = True
                optimized_prompt = api_result
            else:
                logger.warning(f"{self.log_prefix} 未知的API返回类型: {type(api_result)}")
                
            logger.info(f"{self.log_prefix} LLM优化结果: 成功={success}, 内容长度={len(optimized_prompt)}")
            
            # 7. 处理优化结果
            if success and optimized_prompt.strip():
                # 清理输出
                clean_prompt = optimized_prompt.strip()
                
                # 提取核心提示词（移除可能的解释性文字）
                if "优化结果" in clean_prompt or ":" in clean_prompt:
                    parts = clean_prompt.split(":")
                    if len(parts) > 1:
                        clean_prompt = parts[-1].strip()
                
                # 确保格式正确
                clean_prompt = (
                    clean_prompt.replace('"', '')
                    .replace('\n', ', ')
                    .replace('**', '')
                    .replace('\\', '')
                    .replace('```', '')  # 移除可能的代码块标记
                )
                
                # 添加基础质量标签（如果缺失）
                if "anime style" not in clean_prompt.lower():
                    clean_prompt = "anime style, " + clean_prompt
                
                logger.info(f"{self.log_prefix} 提示词优化成功: {original_prompt} → {clean_prompt}")
                return clean_prompt

            return f"anime style, {original_prompt}"

        except Exception as e:
            logger.error(f"{self.log_prefix} 提示词优化异常: {str(e)}", exc_info=True)
            return f"anime style, {original_prompt}"

    async def execute(self) -> Tuple[bool, str]:
        """执行智能图片生成"""
        api_key = self.get_config("api.sf_api_key", "default_key")
        image_size = self.get_config("api.sf_image_size", "768x1024")
        logger.info(f"{self.log_prefix} 执行智能图片生成动作")

        # 获取参数
        description = self.action_data.get("description")

        # 参数验证
        if not description:
            error_msg = "图片描述不能为空"
            logger.error(f"{self.log_prefix} {error_msg}")
            await self.send_text("没有指定图片描述呢~")
            return False, error_msg

        # 使用LLM优化提示词
        prompt = await self.optimize_prompt_with_llm(description)

        # 调用图片生成API
        try:
            sf_url = "https://api.siliconflow.cn/v1/images/generations"
            sf_headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            sf_payload = {
                "model": "Kwai-Kolors/Kolors",
                "prompt": prompt,
                "negative_prompt": "lowres, bad anatomy, bad hands, text, error, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, deformed, disfigured, mutation, ugly",
                "image_size": image_size,
                "batch_size": 1,
                "seed": random.randint(1, 9999999999),
                "num_inference_steps": 25,
                "guidance_scale": 7.5,
            }
            
            logger.info(f"{self.log_prefix} 调用SiliconFlow API生成图片，优化后的prompt: {prompt}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(sf_url, headers=sf_headers, json=sf_payload) as resp:
                    if resp.status != 200:
                        error_detail = await resp.text()
                        logger.error(f"SiliconFlow请求失败，状态码: {resp.status}, 返回: {error_detail}")
                        await self.send_text("图片生成失败（参数错误或服务异常）")
                        return False, f"图片生成失败（SiliconFlow请求失败: {error_detail}）"
                    
                    result = await resp.json()
                    img_url = None
                    images = result.get("data", [])
                    
                    if images and isinstance(images, list) and len(images) > 0 and isinstance(images[0], dict):
                        if "url" in images[0]:
                            img_url = images[0]["url"]
                        else:
                            logger.warning(f"SiliconFlow响应中data[0]缺少'url'字段: {result}")
                    else:
                        logger.warning(f"SiliconFlow响应中缺少预期的'data[0].url'结构: {result}")
                        img_url = result["url"]
                    
                    if img_url:
                        try:
                            async with session.get(img_url) as img_resp:
                                if img_resp.status == 200:
                                    img_bytes = await img_resp.read()
                                    base64_image_string = base64.b64encode(img_bytes).decode("utf-8")
                                    await self.send_image(base64_image_string)
                                    logger.info("图片已通过URL下载并转换为Base64发送")
                                    return True, f"已生成并发送图片（URL转Base64），prompt: {prompt}"
                        except Exception as e:
                            logger.error(f"图片下载或Base64转换失败: {e}")
                            await self.send_text("图片下载或处理失败")
                            return False, f"图片下载或Base64转换失败: {e}"
                    
                    logger.error(f"SiliconFlow生成结果异常: {result}")
                    await self.send_text("图片生成失败（SiliconFlow生成结果异常）")
                    return False, "图片生成失败（SiliconFlow生成结果异常）"
        except Exception as e:
            logger.error(f"生成并发送图片失败: {e}")
            return False, "图片生成或发送失败"

@register_plugin
class SendImagePlugin(BasePlugin):
    # 插件基本信息
    plugin_name = "Send_Image_plugin_sf"
    plugin_description = "发送图片的插件动作，支持通过LLM生成图片并发送，兼容base64和url两种图片返回方式。"
    plugin_version = "0.6.0"
    plugin_author = "yishang"
    enable_plugin = True
    config_file_name = "config.toml"
    dependencies: list[str] = []
    python_dependencies: list[str] = []

    # 配置节描述
    config_section_descriptions = {
        "plugin": "插件启用与版本配置",
        "components": "组件启用控制",
        "api": "图片生成API相关配置",
        "llm": "LLM模型相关配置",
    }

    # 配置Schema定义
    config_schema = {
        "plugin": {
            "enabled": ConfigField(type=bool, default=True, description="是否启用插件"),
            "config_version": ConfigField(type=str, default="1.3.0", description="配置文件版本"),
        },
        "components": {
            "enable_send_image_action": ConfigField(type=bool, default=True, description="是否启用图片生成Action"),
        },
        "api": {
            "sf_api_key": ConfigField(type=str, default="your_api_key", description="SiliconFlow API密钥（必填）", example="sk-xxxx"),
            "image_size": ConfigField(type=str, default="768x1024", description="图片分辨率，格式如768x1024"),
        },
        "llm": {
            "default_model": ConfigField(type=str, default="replyer_1", description="默认使用的LLM模型名称"),
            "optimization_prompt": ConfigField(type=str, default="", description="自定义提示词优化模板，留空使用默认"),
        },
    }

    def __init__(self, plugin_dir=None, *args, **kwargs):
        if plugin_dir is None:
            plugin_dir = os.path.dirname(os.path.abspath(__file__))
        super().__init__(plugin_dir=plugin_dir, *args, **kwargs)

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        """返回插件包含的组件列表"""
        if self.get_config("components.enable_send_image_action", True):
            return [
                (SendImageAction.get_action_info(), SendImageAction),
            ]
        return []
