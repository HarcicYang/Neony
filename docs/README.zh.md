# Neony 文档

> [English documentation](README.en.md)

Neony 是一个处于 pre-beta 阶段的 Python 响应式桌面 UI 框架。本目录按
使用任务组织：新用户先读入门教程，常见功能查阅指南，需要精确签名时再查
API 参考。

## 从这里开始

- [入门教程](getting-started.zh.md) —— 从安装 Neony 开始，逐步构建一个小型
  响应式窗口。
- [安装与平台](guides/installation-platforms.zh.md) —— 系统依赖、平台边界、
  原生对话框和故障排查。
- [示例索引](../readme.zh.md#示例) —— 当前仓库根目录中的可运行示例。

## 指南

指南会按功能逐步补齐。新用户应优先沿着入门教程阅读；在 API 参考拆分为
更小章节期间，现有 API 单文件仍然是完整参考入口。

- [安装与平台](guides/installation-platforms.zh.md)
- [当前 API 参考](api.zh.md)
- [贡献指南](../CONTRIBUTING.zh.md)
- [路线图](../ROADMAP.md)
- [变更记录](../CHANGELOG.md)

## API 参考

- [API 参考（当前单文件入口）](api.zh.md)
- [English API reference](api.en.md)

`api.en.md` 和 `api.zh.md` 会作为稳定入口保留，并逐步迁移为成对的章节
文件。API 符号、导入路径、命令和示例文件名在两种语言中保持原样，方便
直接复制代码。

## 语言与职责

英文和中文使用独立文件，并通过文件头互相链接。新增功能应同步更新两种
语言。教程性解释放在指南中；短签名、参数、返回值和边界行为放在 API
参考中。根目录 README 继续负责项目概览和最短入口。

返回[中文 README](../readme.zh.md)，或阅读 [English README](../readme.md)。
