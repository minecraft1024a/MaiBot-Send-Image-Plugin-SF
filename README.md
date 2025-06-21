# 一个基于硅基流动生图模型的麦麦插件

## 描述
该插件允许用户通过大语言模型生成图片，并将其发送到聊天中。插件支持调用硅基流动的免费API生成图片,~~虽然画人效果不是很好~~，并兼容base64图片返回方式。

## 功能
- **智能图片生成**: 用户可以输入描述，插件将生成相应的图片。
- **多种激活模式**: 支持通过LLM判定和关键词激活。
- **配置灵活**: 用户可以通过配置文件调整API密钥、图片分辨率等参数。

## 安装和使用
1. **安装插件**: 将插件文件夹放置在MaiBot的插件目录中(麦麦安装目录/plugins).
   确保插件目录结构正确。
2. **配置API密钥**: 在`config.toml`文件中，找到以下行并替换`your_api_key`为你的哈基流动密钥。
   ```toml
   [api]
   sf_api_key = your_api_key
   ```
3. **启用插件**: 确保插件在`config.toml`文件中启用。
   ```toml
   [plugin]
   enabled = true
   ```

## 配置选项
- **API密钥**: `sf_api_key` - SiliconFlow API密钥。
- **图片分辨率**: `image_size` - 图片分辨率，格式如`768x1024`。

## 示例
用户输入: "生成一张美丽的日落图片"
插件输出: 生成并发送一张高质量的日落图片。
![示例](https://github.com/minecraft1024a/MaiBot-Send-Image-Plugin-SF/blob/main/Image_1750468252184.png)

## 常见问题
- **API密钥错误**: 确保API密钥正确无误。
- **图片生成失败**: 检查API密钥和网络连接。
- **配置文件错误**: 确保配置文件格式正确。

## 贡献
欢迎贡献代码和报告问题。请访问[GitHub仓库](https://github.com/minecraft1024a/send_image_plugin_sf)获取更多信息。
## 鸣谢
- MaiM-with-u开发组为我们开发如此优质的[麦麦机器人](https://github.com/MaiM-with-u/MaiBot)
- Copilot老师帮我改好这座石山
- 麦麦答疑群(梁山伯)的所有成员
## 许可证
本项目采用MIT许可证。有关详细信息，请参阅[LICENSE](LICENSE)文件。