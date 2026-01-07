# smart-analyze-stream 前端调用代码

## 最简单版本（直接复制使用）

### 场景1：点击选择项（需要生辰信息）

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>智能运势分析</title>
</head>
<body>
    <button onclick="testScenario1()">测试场景1</button>
    <div id="result"></div>

    <script>
        function testScenario1() {
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = '开始请求...';

            // 构建 URL（生产环境）
            const url = 'http://8.210.52.217:8001/api/v1/smart-fortune/smart-analyze-stream?' +
                'category=' + encodeURIComponent('事业财富') +
                '&year=1990' +
                '&month=5' +
                '&day=15' +
                '&hour=14' +
                '&gender=male' +
                '&user_id=test_user_001';

            // 创建 EventSource 连接
            const eventSource = new EventSource(url);

            // 监听状态更新
            eventSource.addEventListener('status', function(e) {
                const data = JSON.parse(e.data);
                resultDiv.innerHTML += '<p>状态: ' + data.message + '</p>';
                console.log('状态:', data);
            });

            // 监听简短答复开始
            eventSource.addEventListener('brief_response_start', function(e) {
                resultDiv.innerHTML += '<h3>简短答复:</h3>';
            });

            // 监听简短答复内容（流式）
            eventSource.addEventListener('brief_response_chunk', function(e) {
                const data = JSON.parse(e.data);
                resultDiv.innerHTML += data.content;
            });

            // 监听简短答复结束
            eventSource.addEventListener('brief_response_end', function(e) {
                const data = JSON.parse(e.data);
                resultDiv.innerHTML += '<p><strong>完整答复:</strong> ' + data.content + '</p>';
            });

            // 监听预设问题列表
            eventSource.addEventListener('preset_questions', function(e) {
                const data = JSON.parse(e.data);
                resultDiv.innerHTML += '<h3>预设问题:</h3><ul>';
                data.questions.forEach(function(q) {
                    resultDiv.innerHTML += '<li>' + q + '</li>';
                });
                resultDiv.innerHTML += '</ul>';
            });

            // 监听性能数据
            eventSource.addEventListener('performance', function(e) {
                const data = JSON.parse(e.data);
                resultDiv.innerHTML += '<p>总耗时: ' + data.total_time_ms + 'ms</p>';
            });

            // 监听错误
            eventSource.addEventListener('error', function(e) {
                const data = JSON.parse(e.data);
                resultDiv.innerHTML += '<p style="color:red">错误: ' + data.message + '</p>';
                eventSource.close();
            });

            // 监听结束
            eventSource.addEventListener('end', function(e) {
                resultDiv.innerHTML += '<p>完成</p>';
                eventSource.close();
            });

            // 连接错误处理
            eventSource.onerror = function(error) {
                resultDiv.innerHTML += '<p style="color:red">连接错误</p>';
                eventSource.close();
            };
        }
    </script>
</body>
</html>
```

### 场景2：点击预设问题（从会话缓存获取生辰信息）

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>智能运势分析</title>
</head>
<body>
    <button onclick="testScenario2()">测试场景2</button>
    <div id="result"></div>

    <script>
        function testScenario2() {
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = '开始请求...';

            // 构建 URL（生产环境）
            const url = 'http://8.210.52.217:8001/api/v1/smart-fortune/smart-analyze-stream?' +
                'category=' + encodeURIComponent('事业财富') +
                '&question=' + encodeURIComponent('我今年的事业运势如何？') +
                '&user_id=test_user_001';

            // 创建 EventSource 连接
            const eventSource = new EventSource(url);

            // 监听所有事件（同上场景1）
            eventSource.addEventListener('status', function(e) {
                const data = JSON.parse(e.data);
                resultDiv.innerHTML += '<p>状态: ' + data.message + '</p>';
            });

            eventSource.addEventListener('brief_response_start', function(e) {
                resultDiv.innerHTML += '<h3>简短答复:</h3>';
            });

            eventSource.addEventListener('brief_response_chunk', function(e) {
                const data = JSON.parse(e.data);
                resultDiv.innerHTML += data.content;
            });

            eventSource.addEventListener('brief_response_end', function(e) {
                const data = JSON.parse(e.data);
                resultDiv.innerHTML += '<p><strong>完整答复:</strong> ' + data.content + '</p>';
            });

            eventSource.addEventListener('preset_questions', function(e) {
                const data = JSON.parse(e.data);
                resultDiv.innerHTML += '<h3>预设问题:</h3><ul>';
                data.questions.forEach(function(q) {
                    resultDiv.innerHTML += '<li>' + q + '</li>';
                });
                resultDiv.innerHTML += '</ul>';
            });

            eventSource.addEventListener('error', function(e) {
                const data = JSON.parse(e.data);
                resultDiv.innerHTML += '<p style="color:red">错误: ' + data.message + '</p>';
                eventSource.close();
            });

            eventSource.addEventListener('end', function(e) {
                resultDiv.innerHTML += '<p>完成</p>';
                eventSource.close();
            });

            eventSource.onerror = function(error) {
                resultDiv.innerHTML += '<p style="color:red">连接错误</p>';
                eventSource.close();
            };
        }
    </script>
</body>
</html>
```

## 完整版本（包含所有事件类型）

```javascript
// 场景1：点击选择项
function callSmartAnalyzeStreamScenario1(category, year, month, day, hour, gender, userId, onUpdate) {
    const url = 'http://8.210.52.217:8001/api/v1/smart-fortune/smart-analyze-stream?' +
        'category=' + encodeURIComponent(category) +
        '&year=' + year +
        '&month=' + month +
        '&day=' + day +
        '&hour=' + hour +
        '&gender=' + gender +
        '&user_id=' + userId;

    const eventSource = new EventSource(url);

    eventSource.addEventListener('status', function(e) {
        const data = JSON.parse(e.data);
        onUpdate && onUpdate('status', data);
    });

    eventSource.addEventListener('brief_response_start', function(e) {
        onUpdate && onUpdate('brief_response_start', {});
    });

    eventSource.addEventListener('brief_response_chunk', function(e) {
        const data = JSON.parse(e.data);
        onUpdate && onUpdate('brief_response_chunk', data);
    });

    eventSource.addEventListener('brief_response_end', function(e) {
        const data = JSON.parse(e.data);
        onUpdate && onUpdate('brief_response_end', data);
    });

    eventSource.addEventListener('preset_questions', function(e) {
        const data = JSON.parse(e.data);
        onUpdate && onUpdate('preset_questions', data);
    });

    eventSource.addEventListener('performance', function(e) {
        const data = JSON.parse(e.data);
        onUpdate && onUpdate('performance', data);
    });

    eventSource.addEventListener('error', function(e) {
        const data = JSON.parse(e.data);
        onUpdate && onUpdate('error', data);
        eventSource.close();
    });

    eventSource.addEventListener('end', function(e) {
        onUpdate && onUpdate('end', {});
        eventSource.close();
    });

    eventSource.onerror = function(error) {
        onUpdate && onUpdate('connection_error', { error: error });
        eventSource.close();
    };

    return eventSource; // 返回以便外部可以关闭
}

// 场景2：点击预设问题
function callSmartAnalyzeStreamScenario2(category, question, userId, onUpdate) {
    const url = 'http://8.210.52.217:8001/api/v1/smart-fortune/smart-analyze-stream?' +
        'category=' + encodeURIComponent(category) +
        '&question=' + encodeURIComponent(question) +
        '&user_id=' + userId;

    const eventSource = new EventSource(url);

    // 监听所有事件（同上）
    eventSource.addEventListener('status', function(e) {
        const data = JSON.parse(e.data);
        onUpdate && onUpdate('status', data);
    });

    eventSource.addEventListener('brief_response_chunk', function(e) {
        const data = JSON.parse(e.data);
        onUpdate && onUpdate('brief_response_chunk', data);
    });

    eventSource.addEventListener('preset_questions', function(e) {
        const data = JSON.parse(e.data);
        onUpdate && onUpdate('preset_questions', data);
    });

    eventSource.addEventListener('error', function(e) {
        const data = JSON.parse(e.data);
        onUpdate && onUpdate('error', data);
        eventSource.close();
    });

    eventSource.addEventListener('end', function(e) {
        onUpdate && onUpdate('end', {});
        eventSource.close();
    });

    eventSource.onerror = function(error) {
        onUpdate && onUpdate('connection_error', { error: error });
        eventSource.close();
    };

    return eventSource;
}

// 使用示例
const eventSource = callSmartAnalyzeStreamScenario1(
    '事业财富', 1990, 5, 15, 14, 'male', 'test_user_001',
    function(eventType, data) {
        console.log('事件:', eventType, data);
        if (eventType === 'brief_response_chunk') {
            // 实时显示流式内容
            document.getElementById('output').innerHTML += data.content;
        }
    }
);

// 需要时可以关闭连接
// eventSource.close();
```

## 使用 fetch API（如果需要更多控制）

```javascript
// 使用 fetch API 获取流式数据
async function fetchSmartAnalyzeStream(params) {
    const queryString = Object.keys(params)
        .map(key => key + '=' + encodeURIComponent(params[key]))
        .join('&');
    
    const url = 'http://8.210.52.217:8001/api/v1/smart-fortune/smart-analyze-stream?' + queryString;
    
    const response = await fetch(url);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
            if (line.startsWith('event:')) {
                const eventType = line.substring(6).trim();
                // 处理事件类型
            } else if (line.startsWith('data:')) {
                const data = JSON.parse(line.substring(5).trim());
                // 处理数据
                console.log('收到数据:', data);
            }
        }
    }
}
```

## 事件类型说明

| 事件类型 | 说明 | 数据格式 |
|---------|------|---------|
| `status` | 状态更新 | `{stage: string, message: string}` |
| `brief_response_start` | 简短答复开始 | `{}` |
| `brief_response_chunk` | 简短答复内容块（流式） | `{content: string}` |
| `brief_response_end` | 简短答复结束 | `{content: string}` |
| `preset_questions` | 预设问题列表 | `{questions: string[]}` |
| `performance` | 性能摘要 | `{total_time_ms: number, stages: array}` |
| `error` | 错误 | `{message: string}` |
| `end` | 流结束 | `{}` |

## 生产环境 URL

- 生产环境：`http://8.210.52.217:8001`
- 本地环境：`http://localhost:8001`

## 注意事项

1. **URL 编码**：中文参数必须使用 `encodeURIComponent()` 编码
2. **EventSource**：浏览器原生支持，无需额外库
3. **关闭连接**：记得在完成后调用 `eventSource.close()` 关闭连接
4. **错误处理**：务必监听 `error` 和 `onerror` 事件
5. **跨域问题**：如果跨域，需要服务器配置 CORS




