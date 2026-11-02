# 电商内容运营中枢

一个面向 Codex 和 ChatGPT 桌面端的电商内容运营插件。输入产品知识库、关键词库和真实图片库后，可生成标题、五张平台主图和中英双语询盘详情页，并持续管理素材余量、内容历史、周月经营反馈和受控升级建议。

当前发布版为 **v1.1.0**：标题统一不超过 60 个全角计数单位（纯中文最多30字）；详情页采用“真实图片证据优先”结构，并对车间、品质细节、包装、客户场景四类素材单独预警。

## 包含内容

- 1688及国内电商平台标题生成与校验（60全角计数单位硬上限）；
- 五张平台主图与三种高清尺寸导出；
- 750px、2×导出的图片优先型详情页（场景、品质、车间、包装、客户使用证据）；
- 全产品独立档案与跨版本去重；
- 素材红黄绿预警和补拍清单；
- 周/月经营数据导入和全局报告；
- 跨产品方法升级提案，需人工确认后应用。

## 通过GitHub安装插件

将本仓库上传到GitHub后，替换下面的 `OWNER/REPOSITORY`：

```bash
codex plugin marketplace add OWNER/REPOSITORY
codex plugin add ecommerce-content-portfolio@ecommerce-operations
```

重新启动 ChatGPT/Codex，并新建任务进行测试。

## 通过技能安装器安装

也可以在 Codex 中输入：

```text
使用 $skill-installer，从 GitHub 仓库 OWNER/REPOSITORY 安装
plugins/ecommerce-content-portfolio/skills/operating-ecommerce-content-portfolio
```

## 离线安装

将 `operating-ecommerce-content-portfolio` 整个文件夹复制到：

```text
macOS / Linux: $HOME/.agents/skills/
Windows:        %USERPROFILE%\.agents\skills\
```

确认最终路径直接包含 `SKILL.md`，不要形成双层同名文件夹。安装后重新启动 Codex。

## 调用示例

```text
使用 $operating-ecommerce-content-portfolio

产品知识库：/absolute/path/to/product-library
关键词库：/absolute/path/to/keyword-library
图片库：/absolute/path/to/real-product-images
```

## 数据边界

插件本身不包含具体产品知识库、客户图片、经营反馈或内容运行历史。使用时生成的 `电商内容运营中枢` 数据目录属于业务数据，不应提交到公开仓库。

## 许可

MIT License。参见 [LICENSE](LICENSE)。
