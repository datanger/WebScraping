# SharePoint 安全操作指南

## 🔒 安全原则

**重要提醒：SharePoint 上的文件非常重要，绝对不能产生任何删除、移动、重命名等影响当前状态的操作！**

### 核心安全原则

1. **只读原则**：只能进行查看、预览、下载等只读操作
2. **路径限制**：只能在指定的下载路径下操作，不能向上级文件夹操作
3. **操作白名单**：只允许明确安全的操作，默认拒绝所有未知操作
4. **URL 检查**：严格检查所有 URL，禁止访问危险的管理页面
5. **实时监控**：所有操作都在安全监控下进行
6. **测试模式**：支持测试模式，所有操作需要用户确认

---

## 🚫 严格禁止的操作

### 文件操作类
- ❌ **删除** (delete, remove, 移除)
- ❌ **移动** (move, 剪切, cut)
- ❌ **重命名** (rename, 重命名文件)
- ❌ **复制** (copy, 复制到)
- ❌ **粘贴** (paste, 粘贴到)

### 文件管理类
- ❌ **新建** (new, 创建, create, 新建文件)
- ❌ **上传** (upload, 上载, 上传文件)
- ❌ **编辑** (edit, 修改, modify, 更改)

### 权限管理类
- ❌ **共享** (share, 权限, permission, 访问)
- ❌ **版本管理** (version, 历史, 恢复)
- ❌ **同步** (sync, 同步到)
- ❌ **发布** (publish, 发布到)

### 工作流类
- ❌ **审批** (approve, 拒绝, 工作流, workflow)

---

## ✅ 允许的安全操作

### 查看类
- ✅ **查看** (view, 打开, open)
- ✅ **预览** (preview)
- ✅ **在新窗口中打开** (open in new window)

### 信息类
- ✅ **属性** (properties, 详细信息, details, 信息)

### 下载类
- ✅ **下载** (download)

---

## 🛡️ 安全保护机制

### 1. 操作检查
```python
# 所有操作都会经过安全检查
if not safety_manager.is_safe_action(button_text):
    print("❌ 操作不安全，禁止执行")
    return False
```

### 2. URL 检查
```python
# 禁止访问危险的管理页面
FORBIDDEN_URL_PATTERNS = [
    r"/_layouts/.*/delete\.aspx",
    r"/_layouts/.*/move\.aspx", 
    r"/_layouts/.*/rename\.aspx",
    r"/_layouts/.*/upload\.aspx",
    # ... 更多危险 URL 模式
]
```

### 3. 路径限制
```python
# 下载路径必须在项目目录内
allowed_download_path = Path("downloads").resolve()
if not path.is_relative_to(allowed_download_path):
    return False  # 禁止访问上级目录
```

### 4. 实时监控
```python
# 扫描页面中的所有操作
scan_result = await scan_page_for_safe_actions(page, safety_manager)
if scan_result["unsafe_count"] > 0:
    print("⚠️ 警告：页面包含危险操作")
```

---

## 📋 使用指南

### 1. 安全下载单个文件

```bash
# 使用安全下载器
python scripts/safe_sharepoint_downloader.py \
  --url "https://sharepoint.com/sites/mysite/Shared%20Documents/file.pdf" \
  --download-path "downloads" \
  --browser edge
```

### 2. 扫描文档库（仅查看，不下载）

```bash
# 扫描文档库中的操作
python scripts/safe_sharepoint_downloader.py \
  --url "https://sharepoint.com/sites/mysite/Shared%20Documents" \
  --scan-only \
  --browser edge
```

### 3. 批量安全下载

```bash
# 创建批量下载列表
echo '{
  "file_urls": [
    "https://sharepoint.com/sites/mysite/Shared%20Documents/file1.pdf",
    "https://sharepoint.com/sites/mysite/Shared%20Documents/file2.docx"
  ]
}' > batch_download.json

# 执行批量下载
python scripts/safe_sharepoint_downloader.py \
  --batch-file batch_download.json \
  --download-path "downloads" \
  --browser edge
```

### 4. 在业务脚本中使用安全模块

```python
from sp_automation.safe_operations import SharePointSafetyManager, safe_download_file

# 创建安全管理器
safety_manager = SharePointSafetyManager("downloads")

# 安全下载文件
downloaded_path = await safe_download_file(
    page, 
    safety_manager,
    download_button_text="下载"
)

if downloaded_path:
    print(f"✅ 文件下载成功: {downloaded_path}")
else:
    print("❌ 下载失败或操作不安全")
```

---

## 🔍 安全检查流程

### 1. 操作前检查
- ✅ 检查按钮文本是否在安全列表中
- ✅ 检查 URL 是否安全
- ✅ 检查下载路径是否在允许范围内

### 2. 操作中监控
- ✅ 实时监控页面操作
- ✅ 记录所有下载的文件
- ✅ 检测危险操作并阻止

### 3. 操作后验证
- ✅ 验证下载文件完整性
- ✅ 生成操作日志
- ✅ 提供安全摘要报告

---

## 📊 安全报告示例

```json
{
  "allowed_download_path": "/project/downloads",
  "total_downloaded": 3,
  "downloaded_files": [
    "/project/downloads/document1.pdf",
    "/project/downloads/document2.docx",
    "/project/downloads/document3.xlsx"
  ],
  "forbidden_actions": [
    "删除", "移动", "重命名", "复制", "粘贴",
    "新建", "上传", "编辑", "共享", "权限"
  ],
  "allowed_actions": [
    "下载", "查看", "预览", "打开", "属性"
  ]
}
```

---

## 🧪 测试模式

### 测试模式功能
测试模式提供额外的安全保护，所有操作都需要用户确认：

1. **自动悬停**：程序自动将鼠标移动到目标元素上
2. **操作确认**：显示详细操作信息，等待用户确认
3. **用户选择**：
   - `y/yes/是` - 确认执行操作
   - `n/no/否` - 取消操作
   - `s/skip/跳过` - 跳过所有后续确认

### 启用测试模式
```bash
python scripts/safe_sharepoint_downloader.py \
  --url "https://sharepoint.com/..." \
  --test-mode \
  --allowed-path "Test"
```

### 测试模式工作流程
1. **元素定位** → 程序找到目标元素
2. **自动悬停** → 鼠标移动到元素上
3. **信息显示** → 命令行显示操作详情
4. **用户确认** → 等待用户输入 y/n/s
5. **执行操作** → 根据用户选择执行或取消

---

## ⚠️ 重要提醒

### 1. 使用前确认
- 确认使用的是安全下载器脚本
- 确认下载路径设置正确
- 确认没有启用任何危险操作
- 建议首次使用启用测试模式

### 2. 操作监控
- 始终使用可视化模式（headless=False）
- 观察浏览器中的操作过程
- 注意安全警告信息
- 测试模式下观察鼠标悬停位置

### 3. 异常处理
- 如果出现安全警告，立即停止操作
- 检查操作日志确认没有危险操作
- 如有疑问，联系系统管理员
- 测试模式下可以随时取消操作

### 4. 定期检查
- 定期检查下载的文件
- 验证操作日志的完整性
- 确认没有意外操作
- 测试模式下验证操作正确性

---

## 🆘 紧急情况处理

### 如果发现危险操作
1. **立即停止**：按 Ctrl+C 停止脚本
2. **检查日志**：查看操作日志确认影响范围
3. **联系管理员**：立即联系 SharePoint 管理员
4. **备份检查**：检查是否有文件被意外修改

### 如果下载失败
1. **检查权限**：确认有文件访问权限
2. **检查网络**：确认网络连接正常
3. **检查路径**：确认下载路径设置正确
4. **重试操作**：使用安全模式重试

---

## 📞 技术支持

如果在使用过程中遇到任何问题：

1. **查看日志**：检查操作日志和错误信息
2. **安全扫描**：使用 `--scan-only` 模式检查页面
3. **联系支持**：提供详细的操作日志和错误信息

**记住：安全第一，宁可下载失败也不能进行危险操作！**

---

*文档版本: 1.0*  
*最后更新: 2024年*  
*安全级别: 最高*
