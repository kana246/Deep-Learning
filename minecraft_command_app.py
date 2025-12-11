import streamlit as st
from pathlib import Path
import sys
import os
import importlib.util
import json
from datetime import datetime
import time
import uuid

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

# 正規化プロンプト
NORMALIZATION_PROMPT = """あなたはMinecraftのコマンド生成システムの自然言語正規化エンジンです。
ユーザーの曖昧な入力を、明確な構造化された形式に変換してください。

【出力形式】
「[対象]に[アイテム名/効果名]を[数量]個与える」または「[対象]に[効果名]の効果を付ける」

【対象の種類】
- 自分/me/@p/私/僕/俺 → 自分
- あいつ/他の人/ほかのプレイヤー/あの人/彼/彼女/@a → 他のプレイヤー
- みんな/全員/all/@a → 全プレイヤー
- 最も近い人/@r → 最も近いプレイヤー
- 特定のプレイヤー名(例: Steve, Alex) → [プレイヤー名]
- 対象が省略されている場合 → 自分

【数量の表現】
- 大量に/たくさん/いっぱい → 64個
- 1スタック/スタック → 64個
- 少し/数個/ちょっと → 5個
- 半スタック → 32個
- 具体的な数値があればその数値
- 省略時 → 1個(ただし松明など消耗品は10個)

【Minecraft用語マッピング】
■道具
- 掘るやつ/採掘道具/ツルハシ/つるはし/ピッケル/pick → ピッケル
- 斧/木切るの/伐採道具 → 斧
- 釣り竿/魚釣りたい → 釣り竿
- 水汲むやつ/バケツ → バケツ
- シャベル/スコップ → シャベル

■武器・防具
- 武器/攻撃できるやつ/剣的なの/けん → 剣
- 遠距離武器/弓矢/bow → 弓
- 防具一式/armor/鎧全部 → ヘルメット、チェストプレート、レギンス、ブーツ
- 頭装備/兜/ヘルメット的なやつ → ヘルメット

■ブロック・素材
- 木材/wood/木のブロック → 木材
- 石ころ/cobblestone/丸石 → 丸石
- 光るやつ/明かり/たいまつ/松明/たいまち → 松明
- 土/dirt/土ブロック → 土
- ガラス/透明なブロック → ガラス

■食料
- 食べ物/food/腹減った → パン
- 肉/ステーキ/beef → ステーキ
- パン/bread → パン
- 果物/リンゴ/apple → リンゴ

■特殊アイテム
- 爆弾/爆発するやつ → TNT
- ワープ/瞬間移動アイテム → エンダーパール
- 寝るやつ/respawn地点 → ベッド
- 時計/時間見るやつ/clock → 時計
- 地図/マッピング/map → 地図

■エフェクト（移動・身体能力）
- 足速くして/走りたい/speed/俊敏 → 俊敏
- 高く飛びたい/ジャンプ力up/jump boost → 跳躍
- 遅くして/のろま/slowness → 鈍化
- 泳ぎ速く/水中移動 → 水中移動

■エフェクト（戦闘関連）
- 強くなりたい/攻撃力up/strength/筋力 → 力
- 硬くなりたい/防御/resistance/耐性 → 耐性
- 再生/回復/regeneration/体力戻して → 再生
- 透明になりたい/invisible/見えなく → 透明化
- 光りたい/暗視/night vision/夜見える → 暗視

■エフェクト（その他）
- 水中呼吸/溺れない/water breathing → 水中呼吸
- 落下ダメージなし/軽やか → 低速落下
- 火耐性/fire resistance/燃えない/耐火 → 火炎耐性
- 毒/poison → 毒
- 弱体化/weakness/弱く → 弱体化

■素材の種類
- 木/wooden/wood → 木
- 石/stone → 石
- 鉄/iron/アイアン → 鉄
- 金/golden/gold/ゴールド → 金
- ダイヤ/ダイア/diamond/dia → ダイヤモンド
- ネザライト/netherite → ネザライト

【変換ルール】
1. 対象を特定し、必ず出力に含める
2. 「〜に」「〜へ」で対象を判別
3. 「やる」「あげる」「渡す」「くれ」「ください」→「与える」
4. 「〜したい」「〜になりたい」→「〜の効果を付ける」(対象は自分)
5. 数量を明示的に出力
6. 素材+アイテムの組み合わせは「[素材]の[アイテム]」
7. 防具一式は4つのパーツに展開(それぞれに対象と数量を付ける)
8. 複数要求は「、」で区切る
9. 対象が明示されていない場合は「自分」とする

【注意事項】
- 必ず「[対象]に」を含める
- 数量は必ず明示(「〜個」の形式)
- 対象が複数の場合も「、」で区切って個別に出力
- プレイヤー名が指定されている場合はそのまま使用
- 「自分」「他のプレイヤー」「全プレイヤー」「最も近いプレイヤー」のいずれかに統一
- 正規化された出力のみを返し、説明文は不要

【入力】
{user_input}

【正規化された出力】"""

# AI直接生成プロンプト
DIRECT_GENERATION_PROMPT = """あなたはMinecraftのコマンド生成AIです。ユーザーの自然言語入力から、直接Minecraftコマンドを生成してください。

【重要ルール】
- コマンドのみを出力（説明文や前置きは不要）
- 複数コマンドの場合は改行で区切る
- 統合版（Bedrock Edition）のコマンド形式を使用

【対象セレクター】
- @s または @p : 自分/コマンド実行者
- @a : 全プレイヤー
- @r : ランダムなプレイヤー
- [プレイヤー名] : 特定のプレイヤー

【主要コマンド形式】
■アイテム付与
/give [対象] [アイテムID] [数量]
例: /give @s diamond 1
例: /give @s iron_pickaxe 1

■エフェクト付与
/effect [対象] [効果ID] [秒数] [レベル]
例: /effect @s speed 60 2
例: /effect @a regeneration 30 1

■テレポート
/tp [対象] [x] [y] [z]
/tp [対象] ~ ~10 ~

■ゲームモード変更
/gamemode creative
/gamemode survival

■天気変更
/weather clear
/weather rain
/weather thunder

■時間変更
/time set day
/time set night

【アイテムID例】
- ダイヤモンド: diamond
- パン: bread
- ステーキ: cooked_beef
- 鉄のツルハシ: iron_pickaxe
- ダイヤの剣: diamond_sword
- オークの原木: oak_log
- 松明: torch
- TNT: tnt
- エンダーパール: ender_pearl

【エフェクトID例】
- 俊敏/速度上昇: speed
- 跳躍力上昇: jump_boost
- 力/攻撃力上昇: strength
- 再生: regeneration
- 耐性: resistance
- 透明化: invisibility
- 暗視: night_vision
- 水中呼吸: water_breathing
- 火炎耐性: fire_resistance

【数量の解釈】
- 大量に/たくさん/いっぱい/スタック → 64
- 少し/数個/ちょっと → 5
- 半スタック → 32
- 明示的な数値があればその数値
- 省略時 → 1

【エディション】
現在のエディション: {edition}
※統合版の場合は統合版のコマンド形式を、Java版の場合はJava版の形式を使用

【入力】
{user_input}

【生成されたコマンド】"""

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
    """
    研究用の詳細なデータをGoogle Sheetsに記録
    """
    if not st.session_state.enable_logging:
        return False
    
    try:
        # Google Sheets認証情報を取得
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            credentials_dict = dict(st.secrets["gcp_service_account"])
        else:
            st.warning("⚠️ Google Sheets認証情報が設定されていません")
            return False
        
        # 認証
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
        client = gspread.authorize(credentials)
        
        # スプレッドシートを開く
        spreadsheet_url = st.secrets.get("SPREADSHEET_URL", None)
        if spreadsheet_url:
            spreadsheet = client.open_by_url(spreadsheet_url)
        else:
            spreadsheet = client.open("Minecraft Command Generation Log")
        
        worksheet = spreadsheet.sheet1
        
        # タイムスタンプ
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # データ行を作成（研究用に拡張）
        row_data = [
            timestamp,                                      # A: タイムスタンプ
            st.session_state.session_id,                    # B: セッションID
            user_input,                                     # C: ユーザー入力
            normalized_text or "",                          # D: AI正規化結果
            hybrid_commands or "",                          # E: ハイブリッドコマンド
            ai_direct_commands or "",                       # F: AI単体コマンド
            edition,                                        # G: エディション
            f"{hybrid_time:.2f}" if hybrid_time else "",    # H: ハイブリッド処理時間
            f"{ai_time:.2f}" if ai_time else "",            # I: AI単体処理時間
            hybrid_error or "",                             # J: ハイブリッドエラー
            ai_error or "",                                 # K: AI単体エラー
            used_model or "",                               # L: 使用モデル
            str(user_rating) if user_rating else "",        # M: ユーザー評価（1-5）
            preferred_version or "",                        # N: 好みの版
            user_comment or ""                              # O: コメント
        ]
        
        worksheet.append_row(row_data)
        return True
        
    except Exception as e:
        st.error(f"Google Sheets記録エラー: {e}")
        return False

# ========== ローカルログ記録（フォールバック） ==========
def log_to_local(
    user_input,
    normalized_text,
    hybrid_commands,
    ai_direct_commands,
    edition,
    hybrid_time=None,
    ai_time=None,
    hybrid_error=None,
    ai_error=None,
    used_model=None
):
    """
    ローカルファイルに記録（Google Sheets利用不可の場合）
    """
    try:
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "session_id": st.session_state.session_id,
            "user_input": user_input,
            "normalized_text": normalized_text,
            "hybrid_commands": hybrid_commands,
            "ai_direct_commands": ai_direct_commands,
            "edition": edition,
            "hybrid_time": hybrid_time,
            "ai_time": ai_time,
            "hybrid_error": hybrid_error,
            "ai_error": ai_error,
            "used_model": used_model
        }
        
        # セッション状態にログを保存
        if 'local_logs' not in st.session_state:
            st.session_state.local_logs = []
        
        st.session_state.local_logs.append(log_data)
        
        # 最新100件のみ保持
        if len(st.session_state.local_logs) > 100:
            st.session_state.local_logs = st.session_state.local_logs[-100:]
        
        return True
    except Exception as e:
        st.error(f"ローカルログエラー: {e}")
        return False

# ========== AI正規化関数 ==========
async def normalize_with_gemini(user_input):
    """
    Gemini APIを使ってユーザー入力を正規化
    """
    if not GEMINI_API_KEY:
        return None, None
    
    import aiohttp
    
    # 複数のエンドポイントを試す
    for endpoint in GEMINI_ENDPOINTS:
        try:
            prompt = NORMALIZATION_PROMPT.replace("{user_input}", user_input)
            
            headers = {"Content-Type": "application/json"}
            
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 500,
                }
            }
            
            url = f"{endpoint}?key={GEMINI_API_KEY}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # テキスト抽出
                        candidates = result.get("candidates", [])
                        if candidates and len(candidates) > 0:
                            content = candidates[0].get("content", {})
                            parts = content.get("parts", [])
                            if parts and len(parts) > 0:
                                normalized_text = parts[0].get("text", "").strip()
                                model_name = endpoint.split('models/')[1].split(':')[0]
                                return normalized_text, model_name
                        
                        return None, None
                    elif response.status == 429:
                        continue
                    else:
                        continue
                        
        except Exception as e:
            continue
    
    return None, None

# ========== AI直接生成関数 ==========
async def generate_command_directly(user_input, edition):
    """
    AI単体でコマンドを直接生成
    """
    if not GEMINI_API_KEY:
        return None, None
    
    import aiohttp
    
    # 複数のエンドポイントを試す
    for endpoint in GEMINI_ENDPOINTS:
        try:
            prompt = DIRECT_GENERATION_PROMPT.replace("{user_input}", user_input).replace("{edition}", edition)
            
            headers = {"Content-Type": "application/json"}
            
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 500,
                }
            }
            
            url = f"{endpoint}?key={GEMINI_API_KEY}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # テキスト抽出
                        candidates = result.get("candidates", [])
                        if candidates and len(candidates) > 0:
                            content = candidates[0].get("content", {})
                            parts = content.get("parts", [])
                            if parts and len(parts) > 0:
                                generated_commands = parts[0].get("text", "").strip()
                                model_name = endpoint.split('models/')[1].split(':')[0]
                                return generated_commands, model_name
                        
                        return None, None
                    elif response.status == 429:
                        continue
                    else:
                        continue
                        
        except Exception as e:
            continue
    
    return None, None

# ========== データ読み込み ==========
current_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
files_in_dir = os.listdir(current_dir)

ITEMS = {}
ITEM_CATEGORIES = []
COMMANDS = []
COMMAND_CATEGORIES = []

load_status = {
    'items': False,
    'commands': False,
    'items_error': '',
    'commands_error': ''
}

# item_data.py の読み込み
try:
    item_data_path = os.path.join(current_dir, 'item_data.py')
    
    if os.path.exists(item_data_path):
        spec = importlib.util.spec_from_file_location("item_data", item_data_path)
        item_data = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(item_data)
        
        items_dict = getattr(item_data, 'items', None) or getattr(item_data, 'ITEMS', {})
        ITEMS = items_dict
        ITEM_CATEGORIES = getattr(item_data, 'categories', None) or getattr(item_data, 'CATEGORIES', [])
        
        if not ITEM_CATEGORIES and ITEMS:
            ITEM_CATEGORIES = list(set([item.get('category', 'その他') for item in ITEMS.values()]))
            ITEM_CATEGORIES.sort()
        
        load_status['items'] = True
        load_status['items_count'] = len(ITEMS)
    else:
        load_status['items_error'] = f"ファイルが見つかりません: {item_data_path}"
        
except Exception as e:
    load_status['items_error'] = str(e)

# command_data.py の読み込み
try:
    command_data_path = os.path.join(current_dir, 'command_data.py')
    
    if os.path.exists(command_data_path):
        spec = importlib.util.spec_from_file_location("command_data", command_data_path)
        command_data = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(command_data)
        
        commands_dict = getattr(command_data, 'commands', None) or getattr(command_data, 'COMMANDS', [])
        
        if isinstance(commands_dict, dict):
            COMMANDS = []
            for cmd_key, cmd_data in commands_dict.items():
                command_entry = {
                    'key': cmd_key,
                    'name': cmd_data.get('name', cmd_key),
                    'desc': cmd_data.get('desc', ''),
                    'keywords': cmd_data.get('aliases', []),
                    'template': cmd_data.get('template', {}),
                    'note': cmd_data.get('note', ''),
                    'category': cmd_data.get('category', 'その他')
                }
                COMMANDS.append(command_entry)
        elif isinstance(commands_dict, list):
            COMMANDS = commands_dict
        
        COMMAND_CATEGORIES = list(set([cmd.get('category', 'その他') for cmd in COMMANDS]))
        COMMAND_CATEGORIES.sort()
        
        load_status['commands'] = True
        load_status['commands_count'] = len(COMMANDS)
    else:
        load_status['commands_error'] = f"ファイルが見つかりません: {command_data_path}"
        
except Exception as e:
    load_status['commands_error'] = str(e)

# ========== コマンド検索関数 ==========
def search_commands(query, edition):
    """
    ユーザーの入力からコマンドを検索
    """
    if not COMMANDS:
        return []
    
    results = []
    query_lower = query.lower()
    
    for cmd in COMMANDS:
        keywords = cmd.get('keywords', []) or cmd.get('aliases', [])
        if any(keyword.lower() in query_lower for keyword in keywords):
            cmd_copy = cmd.copy()
            
            template = cmd_copy.get('template', {})
            
            if isinstance(template, dict):
                cmd_template = template.get(edition, '')
                if isinstance(cmd_template, list):
                    cmd_template = cmd_template[0] if cmd_template else ''
            else:
                cmd_template = template
            
            if '{item_id}' in str(cmd_template):
                if ITEMS:
                    matched_item = None
                    
                    for item_key, item_data in ITEMS.items():
                        item_name = item_data.get('name', '').lower()
                        if item_name in query_lower:
                            matched_item = item_data
                            break
                    
                    if not matched_item:
                        for item_key, item_data in ITEMS.items():
                            aliases = item_data.get('aliases', [])
                            for alias in aliases:
                                if alias.lower() in query_lower:
                                    matched_item = item_data
                                    break
                            if matched_item:
                                break
                    
                    if not matched_item:
                        matched_item = list(ITEMS.values())[0]
                    
                    item_id_data = matched_item.get('id', {})
                    if isinstance(item_id_data, dict):
                        item_id = item_id_data.get(edition, '')
                    else:
                        item_id = item_id_data
                    
                    cmd_copy['cmd'] = cmd_template.replace('{item_id}', item_id)
                    cmd_copy['item_name'] = matched_item.get('name', '')
                    cmd_copy['matched_item_key'] = item_key
                    
                    desc = cmd_copy.get('desc', '')
                    if '{item}' in desc:
                        cmd_copy['desc'] = desc.replace('{item}', matched_item.get('name', ''))
                else:
                    cmd_copy['cmd'] = cmd_template
            else:
                cmd_copy['cmd'] = cmd_template
            
            cmd_copy['cmd_template'] = cmd_template
            
            results.append(cmd_copy)
    
    return results

# ========== ページ設定 ==========
st.set_page_config(
    page_title="Minecraftコマンド生成ツール",
    page_icon="⛏️",
    layout="centered",
)

# CSSスタイル
st.markdown("""
<style>
[data-testid="stSidebar"] {
    position: fixed !important;
    top: 0;
    left: 0;
    width: 280px !important;
    height: 100vh !important;
    background-color: #e8f5e9 !important;
    border-right: 1px solid #e0e0e0;
    padding: 0 !important;
    margin: 0 !important;
    z-index: 1000000;
    overflow: hidden;
    border-radius: 0px 30px 30px 0;
}

[data-testid="stSidebarUserContent"] {
    padding-top: 3rem !important;
    margin-top: 0 !important;
}

[data-testid="stSidebarContent"] {
    overflow-y: auto !important;
    height: 100vh !important;
    padding: 0 1rem 1rem 1rem !important;
    margin: 0 !important;
}

.main {
    margin-left: 280px !important;
}

.block-container {
    max-width: 1200px !important;
    padding-top: 2rem !important;
}

.stButton button {
    width: 100%;
    border-radius: 8px;
    font-weight: 500;
}

@media (max-width: 900px) {
    [data-testid="stSidebar"] {
        position: relative !important;
        width: 100% !important;
        height: auto !important;
        border-right: none !important;
    }
    .main {
        margin-left: 0 !important;
    }
    .block-container {
        max-width: 100% !important;
        padding: 1rem !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ========== セッション状態の初期化 ==========
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'edition' not in st.session_state:
    st.session_state.edition = '統合版'
if 'selected_command' not in st.session_state:
    st.session_state.selected_command = None
if 'user_input' not in st.session_state:
    st.session_state.user_input = ''
if 'generation_mode' not in st.session_state:
    st.session_state.generation_mode = 'both'
if 'enable_logging' not in st.session_state:
    st.session_state.enable_logging = True
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'last_generation_id' not in st.session_state:
    st.session_state.last_generation_id = None

# ========== メイン画面 ==========
st.title("⛏️ Minecraftコマンド生成ツール")
st.markdown("---")

# サイドバーメニュー
st.sidebar.markdown("### 🎮 メニュー")
menu = st.sidebar.radio(
    "機能選択",
    ["🏠 ホーム", "🛠 コマンド生成", "📘 アイテム図鑑", "🧾 コマンド図鑑", "⚙️ 設定"],
    key="main_menu",
    label_visibility="collapsed"
)

# データ読み込み状況を表示
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 データ状況")
st.sidebar.markdown(f"**アイテム:** {len(ITEMS)}個")
st.sidebar.markdown(f"**コマンド:** {len(COMMANDS)}個")
st.sidebar.markdown(f"**エディション:** {st.session_state.edition}")

# ========== ホーム画面 ==========
if menu == "🏠 ホーム":
    st.header("🏠 ホームメニュー")
    
    if load_status['items'] and load_status['commands']:
        st.success(f"✅ データ読み込み成功！")
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.metric("アイテム数", f"{len(ITEMS)}個")
        with col_info2:
            st.metric("コマンド数", f"{len(COMMANDS)}個")
    else:
        st.error("⚠️ データファイルの読み込みに問題があります")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📚 主な機能")
        st.markdown("""
        - 🛠 **コマンド生成**: 日本語でやりたいことを入力
        - 📘 **アイテム図鑑**: アイテム一覧と検索
        - 🧾 **コマンド図鑑**: よく使うコマンド集
        - ⚙️ **設定**: バージョン選択など
        """)
    
    with col2:
        st.markdown("### 🎯 使い方")
        st.markdown("""
        1. 左メニューから機能を選択
        2. やりたいことを日本語で入力
        3. コマンドが自動生成されます
        4. コピー＆ペーストして使用
        """)
    
    st.markdown("---")
    st.markdown("### 📊 研究データ収集について")
    
    if st.session_state.enable_logging:
        st.info("✅ **データ記録: 有効** - あなたの入力と生成結果が研究用に記録されます")
        st.markdown("""
        **記録される情報:**
        - 入力文と生成されたコマンド
        - 処理時間とエラー情報
        - 使用したAIモデル
        - ユーザー評価（任意）
        
        このデータは機械学習モデルの改善に使用されます。
        """)
    else:
        st.warning("⚠️ **データ記録: 無効** - 設定ページで有効にできます")

# ========== コマンド生成画面 ==========
elif menu == "🛠 コマンド生成":
    st.header("🛠 コマンド生成")
    
    if not COMMANDS:
        st.error("❌ コマンドデータが読み込まれていません")
        st.stop()
    
    # 生成モード選択
    st.markdown("### 生成モード選択")
    col_mode1, col_mode2, col_mode3 = st.columns(3)
    
    with col_mode1:
        mode_both = st.button(
            "⚖️ 両方比較（推奨）",
            type="primary" if st.session_state.generation_mode == 'both' else "secondary",
            use_container_width=True,
            help="ハイブリッド版とAI単体版を同時に表示"
        )
        if mode_both:
            st.session_state.generation_mode = 'both'
    
    with col_mode2:
        mode_hybrid = st.button(
            "🔄 ハイブリッド版のみ",
            type="primary" if st.session_state.generation_mode == 'hybrid' else "secondary",
            use_container_width=True,
            help="AI正規化 → ルールベース生成"
        )
        if mode_hybrid:
            st.session_state.generation_mode = 'hybrid'
    
    with col_mode3:
        mode_ai = st.button(
            "🤖 AI単体版のみ",
            type="primary" if st.session_state.generation_mode == 'ai_only' else "secondary",
            use_container_width=True,
            help="AIが直接コマンドを生成"
        )
        if mode_ai:
            st.session_state.generation_mode = 'ai_only'
    
    # 現在のモード表示
    if st.session_state.generation_mode == 'both':
        st.info("⚖️ **比較モード**: ハイブリッド版とAI単体版を同時表示")
    elif st.session_state.generation_mode == 'hybrid':
        st.info("📊 **ハイブリッド版**: AI正規化 → ルールベース生成（精度重視）")
    else:
        st.info("🚀 **AI単体版**: AIが直接コマンドを生成（柔軟性重視）")
    
    st.markdown("---")
    
    # API キーの確認
    if not GEMINI_API_KEY:
        st.error("❌ Gemini APIキーが設定されていません。AI機能を使用するには設定が必要です。")
        st.stop()
    
    st.markdown("### やりたいことを自然な日本語で入力してください")
    
    user_input = st.text_area(
        "入力例",
        value=st.session_state.user_input,
        placeholder="例:\n- パンが欲しい\n- 足を速くしたい\n- ダイヤのツルハシちょうだい\n- みんなに松明を大量に配る",
        height=100,
        key="command_input"
    )
    
    # 処理ボタン
    generate_btn = st.button("🚀 コマンド生成", type="primary", use_container_width=True)
    
    if generate_btn and user_input:
        st.session_state.user_input = user_input
        
        # 生成IDを作成
        generation_id = str(uuid.uuid4())
        st.session_state.last_generation_id = generation_id
        
        # データ記録用の変数
        normalized_text_log = ""
        hybrid_commands_log = ""
        ai_direct_commands_log = ""
        hybrid_time_log = None
        ai_time_log = None
        hybrid_error_log = None
        ai_error_log = None
        used_model_log = None
        
        # ========== 両方比較モード ==========
        if st.session_state.generation_mode == 'both':
            st.markdown("---")
            st.markdown("## 📊 生成結果の比較")
            
            col_result1, col_result2 = st.columns(2)
            
            # 左側: ハイブリッド版
            with col_result1:
                st.markdown("### 🔄 ハイブリッド版")
                st.caption("AI正規化 → ルールベース生成")
                
                with st.spinner("処理中..."):
                    import asyncio
                    
                    # AI正規化
                    hybrid_start = time.time()
                    try:
                        normalized, model_name = asyncio.run(normalize_with_gemini(user_input))
                        if normalized:
                            st.success("✅ 正規化完了")
                            st.info(f"**理解:** {normalized}")
                            search_text = normalized
                            normalized_text_log = normalized
                            used_model_log = model_name
                        else:
                            st.warning("⚠️ 正規化失敗")
                            search_text = user_input
                            hybrid_error_log = "正規化失敗"
                    except Exception as e:
                        st.error(f"エラー: {e}")
                        search_text = user_input
                        hybrid_error_log = str(e)
                    
                    # コマンド検索
                    candidates = search_commands(search_text, st.session_state.edition)
                    hybrid_time_log = time.time() - hybrid_start
                    
                    # ハイブリッドコマンドを記録
                    hybrid_commands_list = []
                    
                    if candidates:
                        for i, cmd in enumerate(candidates):
                            cmd_name = cmd.get('name', cmd.get('desc', 'コマンド'))
                            item_name = cmd.get('item_name', '')
                            
                            if item_name:
                                title = f"{cmd_name}: {item_name}"
                            else:
                                title = f"{cmd_name}"
                            
                            command_text = cmd.get('cmd', '')
                            hybrid_commands_list.append(command_text)
                            
                            with st.container(border=True):
                                st.markdown(f"**{title}**")
                                st.code(command_text, language='bash')
                                
                                with st.expander("詳細"):
                                    st.markdown(f"**解説:** {cmd.get('desc', '')}")
                                    if 'note' in cmd and cmd['note']:
                                        st.markdown(f"**補足:** {cmd['note']}")
                        
                        hybrid_commands_log = " | ".join(hybrid_commands_list)
                        st.success(f"⏱️ 処理時間: {hybrid_time_log:.2f}秒")
                    else:
                        st.warning("⚠️ コマンドが見つかりませんでした")
                        hybrid_error_log = "コマンド未検出"
            
            # 右側: AI単体版
            with col_result2:
                st.markdown("### 🤖 AI単体版")
                st.caption("AIが直接コマンドを生成")
                
                with st.spinner("AIが生成中..."):
                    import asyncio
                    
                    ai_start = time.time()
                    try:
                        generated_commands, model_name = asyncio.run(generate_command_directly(user_input, st.session_state.edition))
                        ai_time_log = time.time() - ai_start
                        
                        if generated_commands:
                            st.success("✅ 生成完了")
                            
                            commands_list = [cmd.strip() for cmd in generated_commands.split('\n') if cmd.strip()]
                            ai_direct_commands_log = " | ".join(commands_list)
                            
                            if not used_model_log:
                                used_model_log = model_name
                            
                            for i, cmd in enumerate(commands_list):
                                with st.container(border=True):
                                    st.markdown(f"**コマンド {i+1}**")
                                    st.code(cmd, language='bash')
                            
                            st.success(f"⏱️ 処理時間: {ai_time_log:.2f}秒")
                        else:
                            st.error("❌ 生成失敗")
                            ai_error_log = "生成失敗"
                    except Exception as e:
                        st.error(f"エラー: {e}")
                        ai_time_log = time.time() - ai_start
                        ai_error_log = str(e)
            
            # Google Sheetsに記録
            if st.session_state.enable_logging:
                with st.spinner("📝 データを記録中..."):
                    if GSPREAD_AVAILABLE:
                        success = log_research_data(
                            user_input,
                            normalized_text_log,
                            hybrid_commands_log,
                            ai_direct_commands_log,
                            st.session_state.edition,
                            hybrid_time=hybrid_time_log,
                            ai_time=ai_time_log,
                            hybrid_error=hybrid_error_log,
                            ai_error=ai_error_log,
                            used_model=used_model_log
                        )
                        if success:
                            st.success("✅ Google Sheetsに記録しました")
                    else:
                        # ローカルログにフォールバック
                        log_to_local(
                            user_input,
                            normalized_text_log,
                            hybrid_commands_log,
                            ai_direct_commands_log,
                            st.session_state.edition,
                            hybrid_time=hybrid_time_log,
                            ai_time=ai_time_log,
                            hybrid_error=hybrid_error_log,
                            ai_error=ai_error_log,
                            used_model=used_model_log
                        )
                        st.info("📝 ローカルログに記録しました（Google Sheets未設定）")
            
            # ユーザーフィードバックUI
            st.markdown("---")
            st.markdown("### 📝 この結果を評価してください（任意）")
            
            col_fb1, col_fb2, col_fb3 = st.columns([2, 2, 3])
            
            with col_fb1:
                user_rating = st.select_slider(
                    "総合評価",
                    options=[1, 2, 3, 4, 5],
                    value=3,
                    help="1: 悪い 〜 5: 良い"
                )
            
            with col_fb2:
                preferred_version = st.radio(
                    "どちらが良かったですか？",
                    ["ハイブリッド版", "AI単体版", "どちらも同じ"],
                    horizontal=True
                )
            
            with col_fb3:
                user_comment = st.text_input(
                    "コメント（任意）",
                    placeholder="改善点や感想など..."
                )
            
            if st.button("📤 フィードバックを送信", use_container_width=True):
                if GSPREAD_AVAILABLE:
                    success = log_research_data(
                        user_input,
                        normalized_text_log,
                        hybrid_commands_log,
                        ai_direct_commands_log,
                        st.session_state.edition,
                        hybrid_time=hybrid_time_log,
                        ai_time=ai_time_log,
                        hybrid_error=hybrid_error_log,
                        ai_error=ai_error_log,
                        used_model=used_model_log,
                        user_rating=user_rating,
                        preferred_version=preferred_version,
                        user_comment=user_comment
                    )
                    if success:
                        st.success("✅ フィードバックを送信しました！ありがとうございます")
                else:
                    st.warning("⚠️ Google Sheets未設定のため、フィードバックを送信できません")
            
            st.markdown("---")
            st.markdown("### 💡 比較ポイント")
            col_compare1, col_compare2 = st.columns(2)
            with col_compare1:
                st.markdown("""
                **ハイブリッド版の強み:**
                - ✅ 高精度なアイテムID
                - ✅ データベースに基づく確実性
                - ✅ 詳細な解説付き
                """)
            with col_compare2:
                st.markdown("""
                **AI単体版の強み:**
                - ✅ 複雑な要求に対応
                - ✅ 柔軟な解釈
                - ✅ データベース不要
                """)

# ========== 設定画面 ==========
elif menu == "⚙️ 設定":
    st.header("⚙️ 設定")
    
    st.markdown("### Minecraftバージョン")
    edition = st.radio(
        "バージョンを選択",
        ["統合版", "Java版"],
        index=0 if st.session_state.edition == "統合版" else 1,
        key="edition_selector"
    )
    st.session_state.edition = edition
    
    st.success(f"✅ 現在のバージョン: **{st.session_state.edition}**")
    
    st.markdown("---")
    st.markdown("### 📝 研究用データ記録設定")
    
    enable_log = st.toggle(
        "📊 データをGoogle Sheetsに記録",
        value=st.session_state.enable_logging,
        help="入力文と生成結果を記録（機械学習研究用）"
    )
    st.session_state.enable_logging = enable_log
    
    if enable_log:
        st.success("✅ データ記録: 有効")
        
        with st.expander("📋 記録される情報の詳細"):
            st.markdown("""
            ### 📊 記録項目一覧
            
            | カラム | 内容 | 例 |
            |--------|------|-----|
            | A | タイムスタンプ | 2024-01-15 14:30:00 |
            | B | セッションID | abc123... |
            | C | ユーザー入力 | パンが欲しい |
            | D | AI正規化結果 | 自分にパンを1個与える |
            | E | ハイブリッドコマンド | /give @s bread 1 |
            | F | AI単体コマンド | /give @s bread 1 |
            | G | エディション | 統合版 |
            | H | ハイブリッド処理時間 | 1.23秒 |
            | I | AI単体処理時間 | 0.98秒 |
            | J | ハイブリッドエラー | （エラー内容） |
            | K | AI単体エラー | （エラー内容） |
            | L | 使用モデル | gemini-1.5-flash |
            | M | ユーザー評価 | 1-5 |
            | N | 好みの版 | ハイブリッド版/AI単体版 |
            | O | コメント | （ユーザーの感想） |
            
            ### 🎯 研究での活用方法
            - **精度評価**: エラー率の比較
            - **速度評価**: 処理時間の分析
            - **ユーザー評価**: フィードバックの集計
            - **モデル改善**: 訓練データとして使用
            """)
        
        # Google Sheets設定状況
        if GSPREAD_AVAILABLE:
            if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
                st.success("✅ Google Sheets API: 設定済み")
                
                # スプレッドシートURL確認
                spreadsheet_url = st.secrets.get("SPREADSHEET_URL", None)
                if spreadsheet_url:
                    st.info(f"📊 記録先: [スプレッドシートを開く]({spreadsheet_url})")
                else:
                    st.warning("⚠️ SPREADSHEET_URLが設定されていません")
                
                # セッション情報
                st.markdown("---")
                st.markdown("### 🔑 セッション情報")
                st.code(f"セッションID: {st.session_state.session_id}")
                st.caption("このIDで同一ユーザーの複数の入力を追跡できます")
                
            else:
                st.warning("⚠️ Google Sheets API: 未設定")
                
                with st.expander("🔧 設定方法（詳細）"):
                    st.markdown("""
                    ### Google Sheets連携の設定手順
                    
                    #### 1️⃣ Google Cloud Projectを作成
                    1. https://console.cloud.google.com/ にアクセス
                    2. 新しいプロジェクトを作成
                    3. プロジェクト名: 例「Minecraft Command Research」
                    
                    #### 2️⃣ APIを有効化
                    1. 「APIとサービス」→「ライブラリ」
                    2. 以下を検索して有効化:
                       - **Google Sheets API**
                       - **Google Drive API**
                    
                    #### 3️⃣ サービスアカウントを作成
                    1. 「APIとサービス」→「認証情報」
                    2. 「認証情報を作成」→「サービスアカウント」
                    3. 名前: 例「minecraft-sheets-writer」
                    4. 役割: 「編集者」
                    5. JSONキーをダウンロード
                    
                    #### 4️⃣ スプレッドシートを作成
                    1. Google Sheetsで新規作成
                    2. タイトル: `Minecraft Command Generation Log`
                    3. **ヘッダー行（A1〜O1）**:
                    ```
                    タイムスタンプ | セッションID | ユーザー入力 | AI正規化結果 | ハイブリッドコマンド | AI単体コマンド | エディション | ハイブリッド処理時間 | AI単体処理時間 | ハイブリッドエラー | AI単体エラー | 使用モデル | 評価 | 好みの版 | コメント
                    ```
                    4. サービスアカウントのメールアドレスに**編集権限**を付与
                       - 例: `minecraft-sheets-writer@your-project.iam.gserviceaccount.com`
                    
                    #### 5️⃣ Streamlit Secretsに追加
                    Streamlit Cloud → Settings → Secrets に以下を追加:
                    
                    ```toml
                    # Gemini API Key
                    GEMINI_API_KEY = "AIzaSy..."
                    
                    # Spreadsheet URL
                    SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/..."
                    
                    # Google Cloud Service Account
                    # （ダウンロードしたJSONの内容をコピペ）
                    [gcp_service_account]
                    type = "service_account"
                    project_id = "your-project-id"
                    private_key_id = "..."
                    private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
                    client_email = "minecraft-sheets-writer@your-project.iam.gserviceaccount.com"
                    client_id = "..."
                    auth_uri = "https://accounts.google.com/o/oauth2/auth"
                    token_uri = "https://oauth2.googleapis.com/token"
                    auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
                    client_x509_cert_url = "..."
                    ```
                    
                    #### 6️⃣ テスト
                    1. アプリを再起動
                    2. コマンドを1回生成
                    3. スプレッドシートに行が追加されていればOK✅
                    """)
        else:
            st.error("❌ gspreadライブラリがインストールされていません")
            st.code("requirements.txt に以下を追加:\ngspread\noauth2client")
        
        # ローカルログのダウンロード
        if 'local_logs' in st.session_state and st.session_state.local_logs:
            st.markdown("---")
            st.markdown("### 💾 ローカルログ")
            st.info(f"📝 {len(st.session_state.local_logs)}件のログが保存されています")
            
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                if st.button("📥 JSONでダウンロード", use_container_width=True):
                    log_json = json.dumps(st.session_state.local_logs, ensure_ascii=False, indent=2)
                    st.download_button(
                        label="💾 ダウンロード開始",
                        data=log_json,
                        file_name=f"command_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
            
            with col_dl2:
                if st.button("🗑️ ローカルログをクリア", use_container_width=True):
                    st.session_state.local_logs = []
                    st.success("✅ ローカルログをクリアしました")
                    st.rerun()
    else:
        st.info("ℹ️ データ記録: 無効")
    
    st.markdown("---")
    st.markdown("### 🤖 AI機能設定")
    
    st.markdown("**Gemini API キー**")
    if GEMINI_API_KEY:
        st.success("✅ APIキーが設定されています")
        masked_key = f"{GEMINI_API_KEY[:10]}...{GEMINI_API_KEY[-4:]}"
        st.code(masked_key)
    else:
        st.warning("⚠️ APIキーが未設定です")
        st.info("Streamlit Cloudの場合: Settings → Secrets に `GEMINI_API_KEY = 'your-api-key'` を追加")
        st.info("ローカルの場合: 環境変数 `GEMINI_API_KEY` を設定")
    
    with st.expander("📖 Gemini APIキーの取得方法"):
        st.markdown("""
        1. [Google AI Studio](https://aistudio.google.com/app/apikey) にアクセス
        2. 「Create API Key」をクリック
        3. APIキーをコピー（`AIzaSy...`で始まる）
        4. Streamlit Secretsに追加:
        ```toml
        GEMINI_API_KEY = "AIzaSy..."
        ```
        """)

# フッター
st.markdown("---")
st.markdown("*Minecraftコマンド生成ツール - 研究用データ収集機能付き*")
st.markdown("🎮 統合版・Java版両対応 | 📊 研究データ自動記録")
