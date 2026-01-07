import streamlit as st
from pathlib import Path
import sys
import os
import importlib.util
import json
from datetime import datetime
import time
import uuid
import asyncio

# Google Sheets API用
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

# Gemini APIの設定
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", None) if hasattr(st, 'secrets') else os.getenv("GEMINI_API_KEY")
GEMINI_ENDPOINTS = [
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
]

# 正規化プロンプト (変更なし)
NORMALIZATION_PROMPT = """指示
あなたはMinecraftの「give」コマンド生成に特化した自然言語正規化エンジンです。
ユーザーの曖昧な入力から、「誰が」「何を」「いくつ」必要としているかを推論し、
以下の正規化形式に変換してください。
### 【正規化形式】
[対象]に[アイテム名]を[数量]個与える
※ 複数のアイテムが必要な場合は「、」で区切り、1行で出力してください。
※ 説明や挨拶は一切禁止します。

### 【対象の正規化】
- 自分/me/@p/私/僕/ここ → 自分
- みんな/全員/all/@a/全員に → 全対象
- 誰か/ランダム/@r → ランダムなプレイヤー
- 固有名(Steve等) → そのプレイヤー名
- 省略時 → 自分
### 【正規化形式】
[対象]に[アイテム名]を[数量]個与える
※ 複数の独立した要求がある場合は、改行で区切って出力してください。
例：
自分にパンを1個与える
みんなにダイヤモンドのツルハシを1個与える
※ 説明や挨拶は一切禁止します。
### 【数量の正規化】
- 1スタック/いっぱい/大量/山ほど → 64個
- 半スタック/半分くらい → 32個
- 少し/ちょっと/数個 → 5個
- 具体的な数字(10個、1つ等) → その数値
- 省略時 → 1個

### 【アイテム名の推論・正規化ルール】

ユーザーの「目的」や「状態」から最適なアイテムを選択してください。
ただしアイテム名が指定されている場合は指定されたアイテムを出力する
■ 1. 状態・困りごとからの推論
- お腹がすいた/腹減った/食べ物 → ステーキ
- 死にそう/体力がやばい/回復したい → 金のリンゴ
- 暗い/見えない/松明 → 松明
- 溺れる/息ができない → 水中呼吸のポーション
- 燃えてる/熱い → 耐火のポーション

■ 2. 目的・作業からの推論
- 掘りたい/採掘したい/ダイヤ掘る → ダイヤモンドのツルハシ
- 木を切りたい/伐採 → ダイヤモンドの斧
- 戦いたい/武器がほしい/敵を倒す → ダイヤモンドの剣
- 守りを固めたい/防具/装備 → ダイヤモンドのヘルメット、ダイヤモンドのチェストプレート、ダイヤモンドのレギンス、ダイヤモンドのブーツ
- 遠くを攻撃したい → 弓、矢
- 建築したい/家を建てたい/ブロック → 石レンガ、オークの原木
- 畑を作りたい/農業 → ダイヤモンドのクワ、小麦の種
- 爆破したい/壊したい → TNT、打ち金
- 遠くへ行きたい/飛びたい → エリトラ、ロケット花火
- 海を渡りたい → オークのボート

■ 3. 素材・通称の変換
- ダイヤ → ダイヤモンド
- 金 → 金インゴット
- 鉄 → 鉄インゴット
- 銅 → 銅インゴット
- 石炭/チャコール → 石炭
- 木/ウッド → オークの原木
- 土/泥 → 土
- 砂 → 砂
### 【対象外の要求】
giveコマンド以外（エフェクト付与、テレポート、天候変更、モブ召喚など）は「対象外」と出力
### 【推論の優先順位】
1. 具体的なアイテム名がある場合はそれを優先。
2. 「〜したい」「〜がない」という表現から、それを解決する最も強力/一般的なアイテムを選択。
3. 数量の指定がない場合、そのアイテムの一般的な使用単位（ツールなら1、消耗品なら複数）を割り当てる。

### 【入力】
{user_input}

### 【正規化された出力】
"""

# AI直接生成プロンプト (変更なし)
DIRECT_GENERATION_PROMPT = """あなたはMinecraftのコマンド生成AIです。ユーザーの自然言語入力から、直接Minecraftコマンドを生成してください。

【重要ルール】
- コマンドのみを出力（説明文や前置きは不要）
- 複数コマンドの場合は改行で区切る
- **giveコマンドのみ**を出力（/give @s <item_id> <amount>）
- 入力された分から意図を理解し、ユーザーが欲しい適切なコマンドを出力

【エディション】
現在のエディション: {edition}
※統合版の場合は統合版のコマンド形式を、Java版の場合はJava版の形式を使用

【入力】
{user_input}

【生成されたコマンド】

"""

# ========== 研究用データ記録関数（拡張版） ==========
def log_research_data(
    user_input,
    normalized_text,
    hybrid_commands,
    ai_direct_commands,
    edition,
    hybrid_time=None,
    ai_time=None,
    hybrid_error=None,
    ai_error=None,
    used_model=None,
    user_rating=None,
    preferred_version=None,
    user_comment=None
):
    if not st.session_state.enable_logging:
        return False
    
    try:
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            credentials_dict = dict(st.secrets["gcp_service_account"])
        else:
            return False
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
        client = gspread.authorize(credentials)
        
        spreadsheet_url = st.secrets.get("SPREADSHEET_URL", None)
        spreadsheet = client.open_by_url(spreadsheet_url) if spreadsheet_url else client.open("Minecraft Command Generation Log")
        worksheet = spreadsheet.sheet1
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_data = [
            timestamp,
            st.session_state.session_id,
            user_input,
            normalized_text or "",
            hybrid_commands or "",
            ai_direct_commands or "",
            edition,
            f"{hybrid_time:.2f}" if hybrid_time else "",
            f"{ai_time:.2f}" if ai_time else "",
            hybrid_error or "",
            ai_error or "",
            used_model or "",
            str(user_rating) if user_rating else "",
            preferred_version or "",
            user_comment or ""
        ]
        worksheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"Google Sheets記録エラー: {e}")
        return False

# ========== ローカルログ記録（フォールバック） ==========
def log_to_local(user_input, normalized_text, hybrid_commands, ai_direct_commands, edition, **kwargs):
    try:
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "session_id": st.session_state.session_id,
            "user_input": user_input,
            "normalized_text": normalized_text,
            "hybrid_commands": hybrid_commands,
            "ai_direct_commands": ai_direct_commands,
            "edition": edition,
            **kwargs
        }
        if 'local_logs' not in st.session_state:
            st.session_state.local_logs = []
        st.session_state.local_logs.append(log_data)
        return True
    except:
        return False

# ========== AI関数群 (async版) ==========
async def normalize_with_gemini(user_input):
    if not GEMINI_API_KEY: return None, None
    import aiohttp
    for endpoint in GEMINI_ENDPOINTS:
        try:
            prompt = NORMALIZATION_PROMPT.replace("{user_input}", user_input)
            data = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}
            url = f"{endpoint}?key={GEMINI_API_KEY}"
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()
                        text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                        return text, endpoint.split('models/')[1].split(':')[0]
        except: continue
    return None, None

async def generate_command_directly(user_input, edition):
    if not GEMINI_API_KEY: return None, None
    import aiohttp
    for endpoint in GEMINI_ENDPOINTS:
        try:
            prompt = DIRECT_GENERATION_PROMPT.replace("{user_input}", user_input).replace("{edition}", edition)
            data = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}}
            url = f"{endpoint}?key={GEMINI_API_KEY}"
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()
                        text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                        return text, endpoint.split('models/')[1].split(':')[0]
        except: continue
    return None, None

# ========== データ読み込み (既存) ==========
current_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
ITEMS, EFFECTS, MOBS, STRUCTURES, COMMANDS = {}, {}, {}, {}, []
load_status = {'items': False, 'effects': False, 'commands': False, 'mobs': False, 'structures': False}

# item_data.py 等のインポート処理 (省略せず維持)
try:
    item_data_path = os.path.join(current_dir, 'item_data.py')
    if os.path.exists(item_data_path):
        spec = importlib.util.spec_from_file_location("item_data", item_data_path)
        item_data = importlib.util.module_from_spec(spec); spec.loader.exec_module(item_data)
        ITEMS = getattr(item_data, 'items', {}) or getattr(item_data, 'ITEMS', {})
        load_status['items'] = True
    
    command_data_path = os.path.join(current_dir, 'command_data.py')
    if os.path.exists(command_data_path):
        spec = importlib.util.spec_from_file_location("command_data", command_data_path)
        command_data = importlib.util.module_from_spec(spec); spec.loader.exec_module(command_data)
        COMMANDS = getattr(command_data, 'commands', []) or getattr(command_data, 'COMMANDS', [])
        load_status['commands'] = True
except: pass

def search_commands(query, edition):
    import re
    if not COMMANDS: return []
    results = []
    query_lower = query.lower()
    target = '@s'
    if any(kw in query_lower for kw in ['みんな', '全員', '@a']): target = '@a'
    
    quantity = 1
    numbers = re.findall(r'\d+', query)
    if numbers: quantity = int(numbers[0])
    elif 'スタック' in query_lower: quantity = 64

    # giveに限定した簡易検索ロジック
    give_cmds = [c for c in COMMANDS if 'give' in str(c.get('key','')).lower()]
    for cmd in give_cmds:
        if '{item_id}' in str(cmd.get('template','')):
            matched_item = None
            for k, v in ITEMS.items():
                if v.get('name','').lower() in query_lower:
                    matched_item = v; break
            if matched_item:
                item_id = matched_item['id'].get(edition, '') if isinstance(matched_item['id'], dict) else matched_item['id']
                cmd_text = f"/give {target} {item_id} {quantity}"
                results.append({'cmd': cmd_text, 'name': 'Give', 'item_name': matched_item['name'], 'desc': cmd.get('desc','')})
    return results

# ========== セッションステート初期化 ==========
if 'session_id' not in st.session_state: st.session_state.session_id = str(uuid.uuid4())
if 'edition' not in st.session_state: st.session_state.edition = '統合版'
if 'enable_logging' not in st.session_state: st.session_state.enable_logging = True
if 'generation_mode' not in st.session_state: st.session_state.generation_mode = 'both'
if 'bulk_results' not in st.session_state: st.session_state.bulk_results = []

# ========== メイン UI ==========
st.title("⛏️ Minecraftコマンド生成ツール")
st.sidebar.markdown("### 🎮 メニュー")
menu = st.sidebar.radio("機能選択", ["🏠 ホーム", "🛠 コマンド生成", "📦 一括検索", "📘 アイテム図鑑", "⚙️ 設定"])

# --- ホーム画面 ---
if menu == "🏠 ホーム":
    st.header("🏠 ホームメニュー")
    st.info(f"現在のエディション: {st.session_state.edition}")
    st.markdown("新機能 **「📦 一括検索」** を追加しました。最大100件のプロンプトを一度に処理し、○×判定を行えます。")

# --- コマンド生成 (既存機能) ---
elif menu == "🛠 コマンド生成":
    st.header("🛠 個別コマンド生成")
    user_input = st.text_area("やりたいことを入力", placeholder="例: 自分にダイヤの剣")
    if st.button("🚀 生成", type="primary") and user_input:
        with st.spinner("生成中..."):
            norm, _ = asyncio.run(normalize_with_gemini(user_input))
            st.write(f"**AIの理解:** {norm}")
            res = search_commands(norm or user_input, st.session_state.edition)
            for r in res:
                st.code(r['cmd'], language='bash')
            
            ai_cmd, _ = asyncio.run(generate_command_directly(user_input, st.session_state.edition))
            if ai_cmd:
                st.markdown("---")
                st.markdown("**AI直接生成:**")
                st.code(ai_cmd, language='bash')

# --- 一括検索 (追加機能) ---
elif menu == "📦 一括検索":
    st.header("📦 一括検索 (最大100件)")
    st.markdown("改行区切りで複数の入力を入れてください。一度に全てのコマンドを生成し、正誤判定を行えます。")
    
    bulk_input = st.text_area("一括入力エリア", height=200, placeholder="ダイヤを10個\nパンを32個\n全員に松明...")
    
    if st.button("🚀 一括処理開始", type="primary"):
        lines = [line.strip() for line in bulk_input.split('\n') if line.strip()][:100]
        if not lines:
            st.warning("入力が空です")
        else:
            new_results = []
            progress_bar = st.progress(0)
            for i, line in enumerate(lines):
                # ハイブリッド処理
                norm, model = asyncio.run(normalize_with_gemini(line))
                hyb_res = search_commands(norm or line, st.session_state.edition)
                hyb_cmd = hyb_res[0]['cmd'] if hyb_res else "検出失敗"
                
                # AI直接生成
                ai_cmd, _ = asyncio.run(generate_command_directly(line, st.session_state.edition))
                
                new_results.append({
                    "input": line,
                    "norm": norm,
                    "hybrid": hyb_cmd,
                    "ai_only": ai_cmd or "生成失敗",
                    "eval": "未評価",
                    "model": model
                })
                progress_bar.progress((i + 1) / len(lines))
            st.session_state.bulk_results = new_results
            st.success(f"{len(lines)} 件の処理が完了しました")

    if st.session_state.bulk_results:
        st.markdown("---")
        st.subheader("📋 生成結果と評価")
        
        # 評価用のテーブル形式UI
        for idx, item in enumerate(st.session_state.bulk_results):
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**入力 {idx+1}:** {item['input']}")
                    st.caption(f"理解: {item['norm']}")
                    st.code(f"HYB: {item['hybrid']}\n AI : {item['ai_only']}", language="bash")
                with col2:
                    # ○×判定
                    res_eval = st.radio(
                        f"判定 #{idx+1}",
                        ["未評価", "○", "×"],
                        key=f"eval_{idx}",
                        horizontal=True,
                        index=["未評価", "○", "×"].index(item['eval'])
                    )
                    st.session_state.bulk_results[idx]['eval'] = res_eval

        # スプレッドシートへの一括書き込み
        if st.button("💾 評価をスプレッドシートに一括保存", use_container_width=True):
            if not GSPREAD_AVAILABLE:
                st.error("Google Sheets APIが利用不可です")
            else:
                with st.spinner("書き込み中..."):
                    success_count = 0
                    for item in st.session_state.bulk_results:
                        rating = 5 if item['eval'] == "○" else (1 if item['eval'] == "×" else 3)
                        success = log_research_data(
                            user_input=item['input'],
                            normalized_text=item['norm'],
                            hybrid_commands=item['hybrid'],
                            ai_direct_commands=item['ai_only'],
                            edition=st.session_state.edition,
                            used_model=item['model'],
                            user_rating=rating,
                            user_comment=f"Eval: {item['eval']}"
                        )
                        if success: success_count += 1
                    st.success(f"{success_count} 件のデータを保存しました！")

# --- 設定画面 (既存) ---
elif menu == "⚙️ 設定":
    st.header("⚙️ 設定")
    st.session_state.edition = st.radio("バージョン選択", ["統合版", "Java版"], index=0 if st.session_state.edition == "統合版" else 1)
    st.session_state.enable_logging = st.toggle("データを記録する", value=st.session_state.enable_logging)
    
    if st.button("ローカルログをダウンロード"):
        if 'local_logs' in st.session_state:
            st.download_button("JSON保存", data=json.dumps(st.session_state.local_logs, ensure_ascii=False), file_name="logs.json")

# フッター
st.markdown("---")
st.caption("Minecraft Command App v2.0 - 一括検索・○×評価対応")
