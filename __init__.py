from src.plugin_system.base.plugin_metadata import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="硅基流动生图插件",
    description="主动思考插件",
    usage="发送图片的插件动作，支持通过硅基流动生成图片并发送，兼容base64图片返回方式。",
    version="1.0.0",
    author="yishang/一闪",
    license="GPL-v3.0-or-later",
    repository_url="https://github.com/minecraft1024a/MaiBot-Send-Image-Plugin-SF",
    keywords=["主动思考", "自己发消息"],
    categories=["Chat", "Integration"],
    extra={"is_built_in": True, "plugin_type": "functional"},
)
