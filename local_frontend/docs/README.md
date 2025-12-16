# 前端开发文档

> **HiFate-bazi 项目前端开发文档和规范**

## 文档目录

### 核心规范

- [开发规范](./开发规范.md) - 前端开发的核心规范，包含代码规范、错误处理、DOM操作、API调用等
- [开发检查清单](./开发检查清单.md) - 开发各阶段的检查清单，确保代码质量

### 问题管理

- [问题复盘模板](./问题复盘模板.md) - 问题复盘的标准模板
- [规范更新流程](./规范更新流程.md) - 规范更新的标准流程

## 快速开始

1. **阅读核心规范**：[开发规范](./开发规范.md)
2. **使用检查清单**：[开发检查清单](./开发检查清单.md)
3. **遇到问题**：使用[问题复盘模板](./问题复盘模板.md)进行复盘

## 工具类使用

### 错误处理

```javascript
// 引入错误处理工具
<script src="js/core/error-handler.js"></script>

// 显示错误
ErrorHandler.showError('错误信息', {
    containerId: 'errorMessage',
    sectionId: 'resultSection',
    scrollTo: true
});

// 处理API错误
ErrorHandler.handleApiError(error, {
    containerId: 'errorMessage',
    sectionId: 'resultSection'
});
```

### DOM操作

```javascript
// 引入DOM工具
<script src="js/core/dom-utils.js"></script>

// 设置文本
DomUtils.setText('elementId', '文本内容');

// 显示/隐藏
DomUtils.show('elementId');
DomUtils.hide('elementId');

// 获取表单值
const value = DomUtils.getFormValue('inputId');
```

### 数据验证

```javascript
// 引入验证工具
<script src="js/core/validator.js"></script>

// 验证八字输入
try {
    Validator.baziInput({
        solar_date: '1990-01-15',
        solar_time: '12:00',
        gender: 'male'
    });
} catch (error) {
    ErrorHandler.showError(error.message);
}
```

## 开发流程

1. **开发前**：阅读规范，理解需求
2. **开发中**：遵循规范，使用工具类
3. **开发后**：完成检查清单
4. **提交前**：确保所有检查项完成
5. **遇到问题**：使用复盘模板记录和总结

## 规范执行

- **强制遵守**：所有代码必须遵循开发规范
- **检查清单**：每次开发必须完成检查清单
- **问题复盘**：所有问题必须复盘并更新规范
- **持续改进**：规范持续优化，适应项目发展

## 相关资源

- [前端代码目录](../)
- [核心工具类](../js/core/)
- [公共样式](../css/common.css)

---

**版本**：v1.0  
**最后更新**：2025-01-XX

