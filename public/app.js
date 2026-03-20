// ====== API通信先設定 ======
// サーバー統合版：同じサーバーから配信されるため空文字（相対パス化）にします
// これにより、ローカル環境(localhost)でも本番環境(Render)でも自動的に正しいURLを参照します！
const API_BASE_URL = '';

// --- 出発地の切り替え（自宅 / 現在地） ---
document.querySelectorAll('input[name="origin-type"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        const originInput = document.getElementById('origin');
        const status = document.getElementById('location-status');
        
        if (e.target.value === 'home') {
            originInput.value = "横浜市南区清水ケ丘98";
            originInput.readOnly = false;
            status.classList.add('hidden');
        } else {
            originInput.value = "📍 現在地を取得中...";
            originInput.readOnly = true;
            status.classList.add('hidden');
            
            // ブラウザのGPS機能にアクセス
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        const lat = position.coords.latitude;
                        const lng = position.coords.longitude;
                        // 緯度経度をそのまま出発地としてGoogle APIやGeminiに投げる！
                        originInput.value = `${lat},${lng}`; 
                        status.innerText = "✅ スマホの現在地を取得しました";
                        status.classList.remove('hidden');
                    },
                    (error) => {
                        alert("現在地の取得に失敗しました。スマホの設定で位置情報の使用を許可してください。（※位置情報の取得にはHTTPS接続が必要です）");
                        document.getElementById('origin-home').checked = true;
                        originInput.value = "横浜市南区清水ケ丘98";
                        originInput.readOnly = false;
                    },
                    { enableHighAccuracy: true }
                );
            } else {
                alert("お使いのブラウザは現在地取得に対応していません。");
                document.getElementById('origin-home').checked = true;
                originInput.value = "横浜市南区清水ケ丘98";
                originInput.readOnly = false;
            }
        }
    });
});

// --- AIおまかせ提案（神機能）の処理 ---
document.getElementById('suggest-btn').addEventListener('click', async () => {
    const origin = document.getElementById('origin').value.trim();
    const mode = document.querySelector('input[name="mode"]:checked').value;
    const schedule = document.getElementById('schedule').value.trim() || "今すぐ";
    const maxTime = document.getElementById('max-time').value;
    const suggestBtn = document.getElementById('suggest-btn');
    const suggestResult = document.getElementById('suggest-result');
    const destinationInput = document.getElementById('destination');
    
    suggestBtn.disabled = true;
    suggestBtn.innerText = "✨ AIが複数の候補を熟考中...";
    suggestResult.classList.add('hidden');

    try {
        const response = await fetch(`${API_BASE_URL}/api/suggest`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: mode, schedule: schedule, origin: origin, max_time: maxTime })
        });

        if (!response.ok) throw new Error("Server Error");

        const data = await response.json();
        
        let suggestions = [];
        try {
            let rawText = data.suggestion; 
            rawText = rawText.replace(/```json/g, '').replace(/```/g, '').trim();
            suggestions = JSON.parse(rawText);
            if (!Array.isArray(suggestions)) suggestions = [suggestions];
        } catch(e) {
            console.error("AI JSON Parse Error", e);
            suggestions = [
                { name: "蒔田公園", reason: "AIからの応答が読み取れませんでしたが、近場の定番公園です！" }
            ];
        }

        let html = '<div style="margin-bottom:12px; color:var(--text-secondary); font-size:0.85rem; font-weight:600;">👇タップすると行き先に自動入力されます</div>';
        suggestions.forEach(s => {
            const starsHtml = s.stars ? `<span style="color:var(--warning); margin-left:8px; font-size:0.95rem;">${s.stars}</span>` : '';
            html += `
            <div class="suggestion-card" onclick="document.getElementById('destination').value='${s.name}'; window.scrollTo({top: 0, behavior: 'smooth'});">
                <div class="sugg-title">📍 ${s.name}${starsHtml}</div>
                <div class="sugg-reason">${s.reason}</div>
            </div>
            `;
        });
        suggestResult.innerHTML = html;
        suggestResult.classList.remove('hidden');

    } catch (error) {
        alert("AIへの相談に失敗しました！サーバー(main.py)を再確認してください。");
    } finally {
        suggestBtn.disabled = false;
        suggestBtn.innerText = "✨ 天気・日時からAIに候補を3〜5つ出してもらう";
    }
});

// --- ルート・分析実行の処理 ---
document.getElementById('search-btn').addEventListener('click', async () => {
    const origin = document.getElementById('origin').value.trim();
    const destination = document.getElementById('destination').value.trim();
    const mode = document.querySelector('input[name="mode"]:checked').value;

    if (!origin || !destination) {
        alert("出発地と行き先を入力してください！");
        return;
    }

    const btn = document.getElementById('search-btn');
    const loading = document.getElementById('loading');
    const resultSection = document.getElementById('result-section');
    
    btn.disabled = true;
    btn.innerText = "情報取得中...";
    resultSection.classList.add('hidden');
    loading.classList.remove('hidden');

    try {
        const response = await fetch(`${API_BASE_URL}/api/navigate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ origin, destination, mode })
        });

        if (!response.ok) throw new Error(`サーバーエラー: ${response.status}`);

        const data = await response.json();
        
        // 天気描画
        const w = data.weather;
        let weatherColor = w.wind_speed >= 5 ? 'var(--warning)' : 'var(--success)';
        const weatherHtml = `
            <div class="alert-item">
                <div style="font-size:1.1rem; margin-bottom:12px; font-weight: 600;">
                    🌡️ 気温: ${w.temp}℃ / ${w.description}<br>
                    💨 風速: ${w.wind_speed} m/s
                </div>
                <div style="color: ${weatherColor}; font-weight: 700; font-size: 0.95rem; background: var(--bg-color); padding: 8px; border-radius: 6px;">
                    ${w.alert}
                </div>
            </div>
        `;
        document.getElementById('weather-content').innerHTML = weatherHtml;

        // ルート・駐車場描画
        if (data.route && data.route.route) {
            const rt = data.route.route;
            const durationText = rt.duration_in_traffic ? `${rt.duration_in_traffic}` : rt.duration;
            const trafficLabel = rt.duration_in_traffic ? '所要時間(渋滞考慮)' : '所要時間';

            document.getElementById('route-content').innerHTML = `
                <div class="route-meta">
                    <div><span class="label">${trafficLabel}</span><span class="value">${durationText}</span></div>
                    <div><span class="label">距離</span><span class="value">${rt.distance}</span></div>
                </div>
                <div class="alert-item" style="font-size:0.9rem; color:var(--text-secondary);">
                    到着地点: ${rt.end_address}
                </div>
            `;
            
            const parkContent = document.getElementById('parking-content');
            if (mode === 'car' && data.route.parking && data.route.parking.length > 0) {
                parkContent.classList.remove('hidden');
                const pList = data.route.parking.map(p => `<li>🅿️ ${p.name} <span style="float:right; color:var(--text-secondary);">評価:${p.rating}</span></li>`).join('');
                document.getElementById('parking-list').innerHTML = pList;
            } else {
                parkContent.classList.add('hidden');
            }
        } else {
            document.getElementById('route-content').innerHTML = `<div class="alert-item">ルートが見つかりませんでした。</div>`;
        }

        // Gemini AI分析結果の描画
        let summary = data.analysis.summary;
        summary = summary.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        summary = summary.replace(/\* (.*)/g, '<li>$1</li>');
        summary = summary.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        summary = summary.replace(/\n/g, '<br>');
        
        document.getElementById('ai-content').innerHTML = `<div class="ai-summary-content">${summary}</div>`;

        loading.classList.add('hidden');
        resultSection.classList.remove('hidden');

    } catch (error) {
        console.error("API通信エラー:", error);
        alert("API通信エラー。バックエンドサーバー(main.py)が起動しているか、またはスマホで見ている場合はAPI_BASE_URLのIPアドレスが正しいか確認してください。");
        loading.classList.add('hidden');
    } finally {
        btn.disabled = false;
        btn.innerText = "ルート・口コミAI分析を実行";
    }
});
