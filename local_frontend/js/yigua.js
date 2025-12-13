// 一事一卦逻辑
document.getElementById('yiguaForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const resultDiv = document.getElementById('result');
    resultDiv.innerHTML = '<div class="loading">占卜中...</div>';

    const question = document.getElementById('question').value;

    if (!question.trim()) {
        resultDiv.innerHTML = '<div class="error">请输入要占卜的问题</div>';
        return;
    }

    try {
        const response = await api.post('/bazi/yigua/divinate', {
            question: question
        });

        if (response.success) {
            displayYiguaResult(response);
        } else {
            resultDiv.innerHTML = `<div class="error">${response.error || '占卜失败'}</div>`;
        }
    } catch (error) {
        resultDiv.innerHTML = `<div class="error">${error.message}</div>`;
    }
});

function displayYiguaResult(data) {
    const resultDiv = document.getElementById('result');
    let html = '<div class="gua-result">';
    
    if (data.gua) {
        html += `<div class="gua-name">${data.gua.name}卦</div>`;
        html += '<div class="gua-info">';
        html += `<p><strong>卦数：</strong>第${data.gua.number}卦</p>`;
        html += `<p><strong>拼音：</strong>${data.gua.pinyin}</p>`;
        html += `<p><strong>卦象含义：</strong>${data.gua.meaning}</p>`;
        html += `<p><strong>卦辞：</strong>${data.gua.description}</p>`;
        html += '</div>';
    }
    
    if (data.interpretation) {
        html += `<div class="interpretation">${data.interpretation}</div>`;
    }
    
    if (data.question) {
        html += `<div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px;">`;
        html += `<p><strong>您的问题：</strong>${data.question}</p>`;
        html += `</div>`;
    }
    
    html += '</div>';
    resultDiv.innerHTML = html;
}

