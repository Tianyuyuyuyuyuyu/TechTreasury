# 更新日志

所有重要的更改都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.1.0-beta] - 2024-12-21

### 新增

- 基础图形用户界面
  - 仓库 URL 输入
  - 文件后缀筛选
  - 输出路径选择
  - GitHub Token 输入
  - 下载进度显示
  - 日志窗口
  - 下载模式选择

- 文件下载功能
  - 支持按文件后缀或完整文件名筛选
  - 支持递归扫描仓库目录
  - 支持网页解析和 GitHub API 两种模式
  - 自动处理同名文件
  - 实时显示下载进度
  - 可取消下载任务

- 文件匹配功能
  - 支持多种匹配模式
  - 不区分大小写匹配
  - 支持文件后缀和完整文件名匹配

### 优化

- 添加详细的日志输出
- 优化文件名冲突处理
- 改进错误处理机制
- 优化网络请求逻辑
- 添加下载延迟以避免触发 API 限制

### 修复

- 修复同名文件覆盖问题
- 修复下载进度条显示问题
- 修复 URL 解析错误
- 修复文件路径处理问题
- 修复编码相关问题

### 安全性

- 添加 GitHub Token 密码显示模式
- 改进私有仓库访问机制
- 优化错误信息显示

### 已知问题

- API 模式可能受到 GitHub API 访问限制
- 部分特殊字符的文件名可能导致保存失败
- 下载大量文件时可能出现内存占用过高的情况

## 即将推出

- [ ] 支持批量仓库下载
- [ ] 添加下载历史记录
- [ ] 支持断点续传
- [ ] 添加代理设置
- [ ] 支持自定义文件命名规则
- [ ] 添加文件预览功能
- [ ] 支持更多文件匹配规则
- [ ] 优化内存使用
- [ ] 添加多语言支持
- [ ] 支持自定义主题 