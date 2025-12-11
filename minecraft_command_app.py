import streamlit as st
from pathlib import Path
import sys
import os
import importlib.util
import json
from datetime import datetime

# Google Sheets API用
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

# Gemini APIの設定
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", None) if hasattr(st, 'secrets') else os.getenv("GEMINI_API_KEY")
# Gemini 1.5モデルを優先（2.0はクォータ制限が厳しい）
GEMINI_ENDPOINTS = [
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
]
GEMINI_API_URL = GEMINI_ENDPOINTS[0]  # デフォルト

# 正規化プロンプト（ハイブリッド版用）
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

# AI直接生成プロンプト（AI単体版用）
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

# ========== Google Sheets記録関数 ==========
def log_to_google_sheets(user_input, normalized_text, hybrid_commands, ai_direct_commands, edition):
    """
    Google Spreadsheetsに記録
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
            # スプレッドシート名で開く
            spreadsheet = client.open("Minecraft Command Generation Log")
        
        worksheet = spreadsheet.sheet1
        
        # データを追加
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row_data = [
            timestamp,
            user_input,
            normalized_text or "",
            hybrid_commands or "",
            ai_direct_commands or "",
            edition
        ]
        
        worksheet.append_row(row_data)
        return True
        
    except Exception as e:
        st.error(f"Google Sheets記録エラー: {e}")
        return False

# ========== ローカルログ記録（フォールバック） ==========
def log_to_local(user_input, normalized_text, hybrid_commands, ai_direct_commands, edition):
    """
    ローカルファイルに記録（Google Sheets利用不可の場合）
    """
    try:
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "normalized_text": normalized_text,
            "hybrid_commands": hybrid_commands,
            "ai_direct_commands": ai_direct_commands,
            "edition": edition
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

# ========== 利用可能なモデルをチェック ==========
async def check_available_models():
    """
    利用可能なGeminiモデルを確認
    """
    if not GEMINI_API_KEY:
        return []
    
    import aiohttp
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    result = await response.json()
                    models = result.get("models", [])
                    # generateContentをサポートするモデルのみ
                    available = [
                        m["name"] for m in models 
                        if "generateContent" in m.get("supportedGenerationMethods", [])
                    ]
                    return available
                else:
                    return []
    except Exception as e:
        st.error(f"モデルチェックエラー: {e}")
        return []

# ========== AI直接生成関数 ==========
async def generate_command_directly(user_input, edition):
    """
    AI単体でコマンドを直接生成
    """
    if not GEMINI_API_KEY:
        return None
    
    import aiohttp
    
    # 複数のエンドポイントを試す
    for endpoint in GEMINI_ENDPOINTS:
        try:
            prompt = DIRECT_GENERATION_PROMPT.replace("{user_input}", user_input).replace("{edition}", edition)
            
            headers = {
                "Content-Type": "application/json",
            }
            
            data = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
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
                                return generated_commands
                        
                        return None
                    elif response.status == 429:
                        # レート制限エラー - 次のモデルを試す
                        st.warning(f"⚠️ {endpoint.split('models/')[1].split(':')[0]}: クォータ超過、次のモデルを試行中...")
                        continue
                    else:
                        continue
                        
        except Exception as e:
            continue
    
    return None

# ========== Gemini API呼び出し関数（正規化用） ==========
async def normalize_with_gemini(user_input):
    """
    Gemini APIを使ってユーザー入力を正規化
    """
    if not GEMINI_API_KEY:
        return None
    
    import aiohttp
    
    error_messages = []
    
    # 複数のエンドポイントを試す
    for endpoint in GEMINI_ENDPOINTS:
        try:
            prompt = NORMALIZATION_PROMPT.replace("{user_input}", user_input)
            
            headers = {
                "Content-Type": "application/json",
            }
            
            data = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 500,
                }
            }
            
            url = f"{endpoint}?key={GEMINI_API_KEY}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # テキスト抽出
                        candidates = result.get("candidates", [])
                        if candidates and len(candidates) > 0:
                            content = candidates[0].get("content", {})
                            parts = content.get("parts", [])
                            if parts and len(parts) > 0:
                                normalized_text = parts[0].get("text", "").strip()
                                # 成功したモデル名を表示
                                model_name = endpoint.split('models/')[1].split(':')[0]
                                st.success(f"✅ 使用モデル: {model_name}")
                                return normalized_text
                        
                        return None
                    elif response.status == 429:
                        # レート制限エラー - 次のモデルを試す
                        model_name = endpoint.split('models/')[1].split(':')[0]
                        error_messages.append(f"**{model_name}**: クォータ超過（429 - Rate Limit）")
                        continue
                    else:
                        model_name = endpoint.split('models/')[1].split(':')[0]
                        error_messages.append(f"**{model_name}**: Status {response.status}")
                        continue
                        
        except Exception as e:
            model_name = endpoint.split('models/')[1].split(':')[0]
            error_messages.append(f"**{model_name}**: {str(e)}")
            continue
    
    # すべて失敗した場合 - 詳細なエラー情報を表示
    if error_messages:
        st.error("❌ すべてのモデルで失敗しました")
        
        with st.expander("🔍 詳細なエラー情報", expanded=False):
            st.markdown("### 各モデルのエラー:")
            for error_msg in error_messages:
                st.markdown(error_msg)
            
            st.markdown("---")
            st.markdown("### 💡 解決方法:")
            st.markdown("""
            **429エラー（クォータ超過）の場合:**
            1. 数分待ってから再試行
            2. 新しいAPIキーを作成
            3. Google AI Studioで使用状況を確認: https://aistudio.google.com/apikey
            
            **その他のエラーの場合:**
            - APIキーが正しいか確認
            - ネットワーク接続を確認
            """)
    
    return None

# 現在のディレクトリとファイル一覧を確認
current_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
files_in_dir = os.listdir(current_dir)

# データ読み込み
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
        
        # items辞書を読み込む（小文字のitemsに対応）
        items_dict = getattr(item_data, 'items', None) or getattr(item_data, 'ITEMS', {})
        
        # 辞書形式をそのまま使用
        ITEMS = items_dict
        
        # カテゴリ情報の取得
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

# command_data.py の読み込み（辞書形式に対応）
try:
    command_data_path = os.path.join(current_dir, 'command_data.py')
    
    if os.path.exists(command_data_path):
        spec = importlib.util.spec_from_file_location("command_data", command_data_path)
        command_data = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(command_data)
        
        # commands辞書を読み込んで、リスト形式に変換
        commands_dict = getattr(command_data, 'commands', None) or getattr(command_data, 'COMMANDS', [])
        
        if isinstance(commands_dict, dict):
            # 辞書形式を内部用のリスト形式に変換
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
        
        # template_requires_item関数も読み込む
        template_requires_item = getattr(command_data, 'template_requires_item', None)
        
        COMMAND_CATEGORIES = list(set([cmd.get('category', 'その他') for cmd in COMMANDS]))
        COMMAND_CATEGORIES.sort()
        
        load_status['commands'] = True
        load_status['commands_count'] = len(COMMANDS)
    else:
        load_status['commands_error'] = f"ファイルが見つかりません: {command_data_path}"
        
except Exception as e:
    load_status['commands_error'] = str(e)

# ページ設定
st.set_page_config(
    page_title="Minecraftコマンド生成ツール",
    page_icon="⛏️",
    layout="centered",
)

# CSSスタイル
st.markdown("""
<style>
/* ====== サイドバー固定 ====== */
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

[data-testid="stSidebar"] * {
    cursor: default !important;
}

[data-testid="stSidebar"] button,
[data-testid="stSidebar"] a,
[data-testid="stSidebar"] input[type="radio"] {
    cursor: pointer !important;
}

/* ====== メインエリア ====== */
.main {
    margin-left: 280px !important;
}

.block-container {
    max-width: 1200px !important;
    padding-top: 2rem !important;
}

/* ====== 見出しのアンカーリンク非表示 ====== */
h1::before, h2::before, h3::before, h4::before {
    content: none !important;
    display: none !important;
}

h1 a, h2 a, h3 a, h4 a {
    display: none !important;
    pointer-events: none !important;
}

[data-testid="stHeaderActionElements"] {
    display: none !important;
}

/* ====== アニメーション無効化 ====== */
* {
    animation-duration: 0s !important;
    animation-delay: 0s !important;
    transition-duration: 0s !important;
}

/* ====== ボタンスタイル ====== */
.stButton button {
    width: 100%;
    border-radius: 8px;
    font-weight: 500;
}

/* ====== スマホ対応 ====== */
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

# セッション状態の初期化
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'edition' not in st.session_state:
    st.session_state.edition = '統合版'
if 'selected_command' not in st.session_state:
    st.session_state.selected_command = None
if 'user_input' not in st.session_state:
    st.session_state.user_input = ''
if 'use_ai_normalization' not in st.session_state:
    st.session_state.use_ai_normalization = True
if 'normalized_text' not in st.session_state:
    st.session_state.normalized_text = ''
if 'generation_mode' not in st.session_state:
    st.session_state.generation_mode = 'both'  # 'hybrid', 'ai_only', or 'both'
if 'enable_logging' not in st.session_state:
    st.session_state.enable_logging = True

# ========== コマンド検索関数 ==========
def search_commands(query, edition):
    """
    ユーザーの入力からコマンドを検索
    
    Args:
        query (str): 検索キーワード
        edition (str): Minecraftエディション（統合版/Java版）
    
    Returns:
        list: マッチしたコマンドのリスト
    """
    if not COMMANDS:
        return []
    
    results = []
    query_lower = query.lower()
    
    for cmd in COMMANDS:
        # キーワードマッチング（aliases/keywordsの両方に対応）
        keywords = cmd.get('keywords', []) or cmd.get('aliases', [])
        if any(keyword.lower() in query_lower for keyword in keywords):
            cmd_copy = cmd.copy()
            
            # テンプレートの取得
            template = cmd_copy.get('template', {})
            
            # エディション別のテンプレートを取得
            if isinstance(template, dict):
                cmd_template = template.get(edition, '')
                # リスト形式の場合は最初の要素を使用
                if isinstance(cmd_template, list):
                    cmd_template = cmd_template[0] if cmd_template else ''
            else:
                cmd_template = template
            
            # アイテムIDの置換が必要な場合
            if '{item_id}' in str(cmd_template):
                if ITEMS:
                    # クエリからアイテムを検索
                    matched_item = None
                    
                    # 1. アイテム名での完全一致検索
                    for item_key, item_data in ITEMS.items():
                        item_name = item_data.get('name', '').lower()
                        if item_name in query_lower:
                            matched_item = item_data
                            break
                    
                    # 2. エイリアスでの検索
                    if not matched_item:
                        for item_key, item_data in ITEMS.items():
                            aliases = item_data.get('aliases', [])
                            for alias in aliases:
                                if alias.lower() in query_lower:
                                    matched_item = item_data
                                    break
                            if matched_item:
                                break
                    
                    # 3. マッチしない場合はデフォルト（最初のアイテム）
                    if not matched_item:
                        matched_item = list(ITEMS.values())[0]
                    
                    # アイテムIDの取得
                    item_id_data = matched_item.get('id', {})
                    if isinstance(item_id_data, dict):
                        item_id = item_id_data.get(edition, '')
                    else:
                        item_id = item_id_data
                    
                    cmd_copy['cmd'] = cmd_template.replace('{item_id}', item_id)
                    cmd_copy['item_name'] = matched_item.get('name', '')
                    cmd_copy['matched_item_key'] = item_key
                    
                    # 説明文のアイテム名も置換
                    desc = cmd_copy.get('desc', '')
                    if '{item}' in desc:
                        cmd_copy['desc'] = desc.replace('{item}', matched_item.get('name', ''))
                else:
                    cmd_copy['cmd'] = cmd_template
            else:
                cmd_copy['cmd'] = cmd_template
            
            # cmd_templateを保持（後でアイテム変更に使用）
            cmd_copy['cmd_template'] = cmd_template
            
            results.append(cmd_copy)
    
    return results

# ========== アイテム検索関数 ==========
def search_items(query, category=None):
    """
    アイテムを検索
    
    Args:
        query (str): 検索キーワード
        category (str): カテゴリフィルター
    
    Returns:
        dict: マッチしたアイテムの辞書
    """
    if not ITEMS:
        return {}
    
    filtered = ITEMS
    
    # キーワード検索（名前とaliasesの両方を検索）
    if query:
        query_lower = query.lower()
        filtered = {}
        for k, v in ITEMS.items():
            # 名前での検索
            if query_lower in v.get('name', '').lower():
                filtered[k] = v
                continue
            # aliasesでの検索
            aliases = v.get('aliases', [])
            if any(query_lower in alias.lower() for alias in aliases):
                filtered[k] = v
                continue
    
    # カテゴリフィルター
    if category and category != "全て":
        filtered = {
            k: v for k, v in filtered.items()
            if v.get('category') == category
        }
    
    return filtered

# ========== メイン画面 ==========

# タイトル
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
    
    # データ読み込み状況を表示
    if load_status['items'] and load_status['commands']:
        st.success(f"✅ データ読み込み成功！")
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.metric("アイテム数", f"{len(ITEMS)}個")
        with col_info2:
            st.metric("コマンド数", f"{len(COMMANDS)}個")
    else:
        st.error("⚠️ データファイルの読み込みに問題があります")
        
        if not load_status['items']:
            st.warning(f"❌ item_data.py: {load_status['items_error']}")
        else:
            st.success(f"✅ item_data.py: {len(ITEMS)}個読み込み成功")
            
        if not load_status['commands']:
            st.warning(f"❌ command_data.py: {load_status['commands_error']}")
        else:
            st.success(f"✅ command_data.py: {len(COMMANDS)}個読み込み成功")
    
    # デバッグ情報を表示
    with st.expander("🔍 デバッグ情報（開発者向け）", expanded=False):
        st.markdown("**現在のディレクトリ:**")
        st.code(current_dir)
        st.markdown("**ディレクトリ内のファイル:**")
        st.code("\n".join(sorted(files_in_dir)))
        st.markdown("**データファイルの存在確認:**")
        st.code(f"item_data.py: {os.path.exists(os.path.join(current_dir, 'item_data.py'))}")
        st.code(f"command_data.py: {os.path.exists(os.path.join(current_dir, 'command_data.py'))}")
    
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
    
    # データ読み込み状況
    if ITEMS and COMMANDS:
        st.success(f"✅ すべてのデータが正常に読み込まれています")
        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            st.info(f"📦 アイテム: {len(ITEMS)}個")
        with col_stat2:
            st.info(f"📋 コマンド: {len(COMMANDS)}個")
    else:
        st.warning("⚠️ 一部のデータが読み込まれていません")
        if not ITEMS:
            st.error(f"❌ item_data.py: {load_status.get('items_error', '不明なエラー')}")
        if not COMMANDS:
            st.error(f"❌ command_data.py: {load_status.get('commands_error', '不明なエラー')}")

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
    if not GEMINI_API_KEY and st.session_state.generation_mode != 'hybrid':
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
        
        # データ記録用の変数
        normalized_text_log = ""
        hybrid_commands_log = ""
        ai_direct_commands_log = ""
        
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
                    if GEMINI_API_KEY:
                        normalized = asyncio.run(normalize_with_gemini(user_input))
                        if normalized:
                            st.success("✅ 正規化完了")
                            st.info(f"**理解:** {normalized}")
                            search_text = normalized
                            normalized_text_log = normalized
                        else:
                            st.warning("⚠️ 正規化失敗")
                            search_text = user_input
                    else:
                        search_text = user_input
                    
                    # コマンド検索
                    candidates = search_commands(search_text, st.session_state.edition)
                    
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
                                
                                # アイテム選択
                                if '{item_id}' in cmd.get('cmd_template', '') and ITEMS:
                                    current_item_key = cmd.get('matched_item_key', list(ITEMS.keys())[0])
                                    item_names = [item.get('name', k) for k, item in ITEMS.items()]
                                    current_item_name = ITEMS.get(current_item_key, {}).get('name', item_names[0])
                                    
                                    try:
                                        default_index = item_names.index(current_item_name)
                                    except ValueError:
                                        default_index = 0
                                    
                                    selected_item = st.selectbox(
                                        "アイテム変更",
                                        options=item_names,
                                        index=default_index,
                                        key=f"hybrid_item_{i}",
                                    )
                                    
                                    for item_key, item in ITEMS.items():
                                        if item.get('name', item_key) == selected_item:
                                            item_id_data = item.get('id', {})
                                            if isinstance(item_id_data, dict):
                                                item_id = item_id_data.get(st.session_state.edition, item_key)
                                            else:
                                                item_id = item_id_data
                                            updated_cmd = cmd['cmd_template'].replace('{item_id}', item_id)
                                            st.code(updated_cmd, language='bash')
                                            break
                                
                                with st.expander("詳細"):
                                    st.markdown(f"**解説:** {cmd.get('desc', '')}")
                                    if 'note' in cmd and cmd['note']:
                                        st.markdown(f"**補足:** {cmd['note']}")
                        
                        hybrid_commands_log = " | ".join(hybrid_commands_list)
                    else:
                        st.warning("⚠️ コマンドが見つかりませんでした")
            
            # 右側: AI単体版
            with col_result2:
                st.markdown("### 🤖 AI単体版")
                st.caption("AIが直接コマンドを生成")
                
                with st.spinner("AIが生成中..."):
                    import asyncio
                    generated_commands = asyncio.run(generate_command_directly(user_input, st.session_state.edition))
                    
                    if generated_commands:
                        st.success("✅ 生成完了")
                        
                        commands_list = [cmd.strip() for cmd in generated_commands.split('\n') if cmd.strip()]
                        ai_direct_commands_log = " | ".join(commands_list)
                        
                        for i, cmd in enumerate(commands_list):
                            with st.container(border=True):
                                st.markdown(f"**コマンド {i+1}**")
                                st.code(cmd, language='bash')
                                
                                with st.expander("特徴"):
                                    st.markdown("- 柔軟な解釈")
                                    st.markdown("- 自動ID変換")
                                    st.markdown("- 複雑な要求対応")
                    else:
                        st.error("❌ 生成失敗")
            
            # Google Sheetsに記録
            if st.session_state.enable_logging:
                with st.spinner("📝 データを記録中..."):
                    if GSPREAD_AVAILABLE:
                        success = log_to_google_sheets(
                            user_input,
                            normalized_text_log,
                            hybrid_commands_log,
                            ai_direct_commands_log,
                            st.session_state.edition
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
                            st.session_state.edition
                        )
                        st.info("📝 ローカルログに記録しました（Google Sheets未設定）")
            
            st.markdown("---")
            st.markdown("### 💡 比較ポイント")
            col_compare1, col_compare2 = st.columns(2)
            with col_compare1:
                st.markdown("""
                **ハイブリッド版の強み:**
                - ✅ 高精度なアイテムID
                - ✅ データベースに基づく確実性
                - ✅ アイテム選択UI
                - ✅ 詳細な解説付き
                """)
            with col_compare2:
                st.markdown("""
                **AI単体版の強み:**
                - ✅ 複雑な要求に対応
                - ✅ 柔軟な解釈
                - ✅ データベース不要
                - ✅ 即座に生成
                """)
        
        # ========== ハイブリッド版のみ ==========
        elif st.session_state.generation_mode == 'hybrid':
            use_ai = GEMINI_API_KEY is not None
            
            if use_ai:
                with st.spinner("🤖 AIが入力を理解しています..."):
                    import asyncio
                    normalized = asyncio.run(normalize_with_gemini(user_input))
                    
                    if normalized:
                        st.session_state.normalized_text = normalized
                        st.success("✅ AI正規化完了")
                        st.info(f"**理解した内容:** {normalized}")
                        search_text = normalized
                    else:
                        st.warning("⚠️ AI正規化に失敗しました。元の入力で検索します。")
                        search_text = user_input
            else:
                search_text = user_input
            
            candidates = search_commands(search_text, st.session_state.edition)
            
            if candidates:
                st.success(f"✅ {len(candidates)}件のコマンドが見つかりました")
                
                for i, cmd in enumerate(candidates):
                    cmd_name = cmd.get('name', cmd.get('desc', 'コマンド'))
                    item_name = cmd.get('item_name', '')
                    
                    if item_name:
                        expander_title = f"📋 {cmd_name}: {item_name}を与える"
                    else:
                        expander_title = f"📋 {cmd_name}: {cmd.get('desc', '')}"
                    
                    with st.expander(expander_title, expanded=(i==0)):
                        st.code(cmd.get('cmd', ''), language='bash')
                        
                        if '{item_id}' in cmd.get('cmd_template', '') and ITEMS:
                            st.markdown("---")
                            st.markdown("**🔄 アイテムを変更:**")
                            
                            current_item_key = cmd.get('matched_item_key', list(ITEMS.keys())[0])
                            item_names = [item.get('name', k) for k, item in ITEMS.items()]
                            current_item_name = ITEMS.get(current_item_key, {}).get('name', item_names[0])
                            
                            try:
                                default_index = item_names.index(current_item_name)
                            except ValueError:
                                default_index = 0
                            
                            selected_item = st.selectbox(
                                "アイテム選択",
                                options=item_names,
                                index=default_index,
                                key=f"item_select_{i}",
                                label_visibility="collapsed"
                            )
                            
                            for item_key, item in ITEMS.items():
                                if item.get('name', item_key) == selected_item:
                                    item_id_data = item.get('id', {})
                                    if isinstance(item_id_data, dict):
                                        item_id = item_id_data.get(st.session_state.edition, item_key)
                                    else:
                                        item_id = item_id_data
                                    updated_cmd = cmd['cmd_template'].replace('{item_id}', item_id)
                                    st.code(updated_cmd, language='bash')
                                    break
                        
                        st.markdown("---")
                        st.markdown(f"**📝 解説:** {cmd.get('desc', '')}")
                        if 'note' in cmd and cmd['note']:
                            st.markdown(f"**💡 補足:** {cmd['note']}")
                        if 'category' in cmd:
                            st.markdown(f"**🏷️ カテゴリ:** {cmd['category']}")
            else:
                st.warning("⚠️ 該当するコマンドが見つかりませんでした")
        
        # ========== AI単体版のみ ==========
        else:
            with st.spinner("🤖 AIがコマンドを生成しています..."):
                import asyncio
                generated_commands = asyncio.run(generate_command_directly(user_input, st.session_state.edition))
                
                if generated_commands:
                    st.success("✅ AI単体版でコマンド生成完了")
                    
                    commands_list = [cmd.strip() for cmd in generated_commands.split('\n') if cmd.strip()]
                    
                    for i, cmd in enumerate(commands_list):
                        with st.expander(f"📋 生成されたコマンド {i+1}", expanded=True):
                            st.code(cmd, language='bash')
                            
                            st.markdown("---")
                            st.markdown("**💡 AI単体版の特徴:**")
                            st.markdown("- 柔軟な解釈が可能")
                            st.markdown("- 複雑な要求に対応")
                            st.markdown("- アイテムIDの変換も自動")
                else:
                    st.error("❌ コマンド生成に失敗しました")

# ========== アイテム図鑑 ==========
elif menu == "📘 アイテム図鑑":
    st.header("📘 アイテム図鑑")
    
    if not ITEMS:
        st.error("❌ アイテムデータが読み込まれていません")
        st.stop()
    
    st.markdown("### アイテム一覧")
    
    # カテゴリフィルターと検索
    col1, col2 = st.columns([2, 1])
    with col1:
        search_query = st.text_input(
            "🔍 アイテムを検索", 
            placeholder="例: 木、オーク、板材",
            help="アイテム名やエイリアス（別名）で検索できます"
        )
    with col2:
        selected_category = st.selectbox(
            "カテゴリ",
            ["全て"] + ITEM_CATEGORIES,
            key="item_category"
        )
    
    # アイテム検索
    filtered_items = search_items(search_query, selected_category)
    
    if filtered_items:
        st.info(f"📦 {len(filtered_items)}個のアイテムが見つかりました")
        
        for item_key, item in filtered_items.items():
            category = item.get('category', 'その他')
            item_name = item.get('name', item_key)
            item_desc = item.get('desc', '')
            
            # エイリアス（別名）の取得
            aliases = item.get('aliases', [])
            alias_display = f"別名: {', '.join(aliases[:5])}" if aliases else ""
            if len(aliases) > 5:
                alias_display += f"...他{len(aliases)-5}個"
            
            with st.expander(f"📦 {item_name} [{category}]", expanded=False):
                if item_desc:
                    st.markdown(f"**説明:** {item_desc}")
                
                col1, col2 = st.columns(2)
                
                # IDの取得
                item_id_data = item.get('id', {})
                
                with col1:
                    st.markdown(f"**統合版ID:**")
                    if isinstance(item_id_data, dict):
                        bedrock_id = item_id_data.get('統合版', item_key)
                    else:
                        bedrock_id = item_id_data
                    st.code(bedrock_id)
                    
                with col2:
                    st.markdown(f"**Java版ID:**")
                    if isinstance(item_id_data, dict):
                        java_id = item_id_data.get('Java版', f'minecraft:{item_key}')
                    else:
                        java_id = item_id_data
                    st.code(java_id)
                
                # スタックサイズ
                stack_size = item.get('stack_size', 64)
                st.markdown(f"**スタックサイズ:** {stack_size}")
                
                # エイリアス表示
                if aliases:
                    with st.expander("🏷️ 検索用エイリアス", expanded=False):
                        st.markdown(", ".join(aliases))
                
                # giveコマンドのサンプル
                st.markdown("**取得コマンド:**")
                current_id = bedrock_id if st.session_state.edition == '統合版' else java_id
                
                col_cmd1, col_cmd2 = st.columns(2)
                with col_cmd1:
                    st.markdown("*1個:*")
                    give_cmd_1 = f"/give @s {current_id} 1"
                    st.code(give_cmd_1, language='bash')
                with col_cmd2:
                    st.markdown(f"*{stack_size}個:*")
                    give_cmd_stack = f"/give @s {current_id} {stack_size}"
                    st.code(give_cmd_stack, language='bash')
    else:
        st.warning("該当するアイテムが見つかりませんでした")

# ========== コマンド図鑑 ==========
elif menu == "🧾 コマンド図鑑":
    st.header("🧾 コマンド図鑑")
    
    if not COMMANDS:
        st.error("❌ コマンドデータが読み込まれていません")
        st.stop()
    
    st.markdown("### よく使うコマンド一覧")
    
    # カテゴリフィルター
    selected_cmd_category = st.selectbox(
        "カテゴリで絞り込み",
        ["全て"] + COMMAND_CATEGORIES,
        key="command_category"
    )
    
    filtered_commands = COMMANDS
    if selected_cmd_category != "全て":
        filtered_commands = [
            cmd for cmd in COMMANDS 
            if cmd.get('category') == selected_cmd_category
        ]
    
    st.info(f"📌 {len(filtered_commands)}個のコマンドが見つかりました")
    
    for i, cmd in enumerate(filtered_commands):
        category_tag = cmd.get('category', 'その他')
        cmd_name = cmd.get('name', cmd.get('desc', 'コマンド'))
        
        # テンプレートの取得
        template = cmd.get('template', {})
        if isinstance(template, dict):
            cmd_template = template.get(st.session_state.edition, '')
            if isinstance(cmd_template, list):
                cmd_template = cmd_template[0] if cmd_template else ''
        else:
            cmd_template = template
        
        with st.expander(f"📌 [{category_tag}] {cmd_name}", expanded=False):
            st.code(cmd_template, language='bash')
            st.markdown(f"**解説:** {cmd.get('desc', '')}")
            if 'note' in cmd and cmd['note']:
                st.markdown(f"**補足:** {cmd['note']}")
            
            # キーワード表示
            keywords = cmd.get('keywords', []) or cmd.get('aliases', [])
            if keywords:
                st.markdown(f"**検索キーワード:** {', '.join(keywords[:10])}")
                if len(keywords) > 10:
                    st.markdown(f"*...他{len(keywords)-10}個*")

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
    st.markdown("### 📝 データ記録設定")
    
    enable_log = st.toggle(
        "📊 データをGoogle Sheetsに記録",
        value=st.session_state.enable_logging,
        help="入力文と生成結果を記録（機械学習研究用）"
    )
    st.session_state.enable_logging = enable_log
    
    if enable_log:
        st.success("✅ データ記録: 有効")
        
        with st.expander("📋 記録される情報"):
            st.markdown("""
            **記録項目:**
            1. 📅 タイムスタンプ
            2. 💬 ユーザー入力（元の文）
            3. 🤖 AI正規化結果
            4. 🔄 ハイブリッド版のコマンド
            5. ⚡ AI単体版のコマンド
            6. 🎮 エディション（統合版/Java版）
            
            **用途:**
            - 機械学習の訓練データ
            - 精度評価・比較分析
            - モデル改善・研究
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
                
            else:
                st.warning("⚠️ Google Sheets API: 未設定")
                
                with st.expander("🔧 設定方法"):
                    st.markdown("""
                    ### Google Sheets連携の設定手順
                    
                    #### 1. Google Cloud Projectを作成
                    - https://console.cloud.google.com/
                    - 新しいプロジェクトを作成
                    
                    #### 2. APIを有効化
                    - Google Sheets API
                    - Google Drive API
                    
                    #### 3. サービスアカウントを作成
                    - JSONキーをダウンロード
                    
                    #### 4. スプレッドシートを作成
                    - 「Minecraft Command Generation Log」という名前
                    - ヘッダー行: タイムスタンプ | ユーザー入力 | AI正規化結果 | ハイブリッドコマンド | AI単体コマンド | エディション
                    - サービスアカウントに編集権限を付与
                    
                    #### 5. Streamlit Secretsに追加
                    ```toml
                    SPREADSHEET_URL = "your-spreadsheet-url"
                    
                    [gcp_service_account]
                    type = "service_account"
                    project_id = "..."
                    private_key = "..."
                    client_email = "..."
                    ...
                    ```
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
    
    # ローカルログの表示
    if 'local_logs' in st.session_state and st.session_state.local_logs:
        with st.expander(f"📜 最近のログ (最新10件)"):
            for i, log in enumerate(reversed(st.session_state.local_logs[-10:])):
                st.markdown(f"**{i+1}. {log.get('timestamp', 'N/A')}**")
                st.markdown(f"- 📝 入力: `{log.get('user_input', '')}`")
                if log.get('normalized_text'):
                    st.markdown(f"- 🤖 正規化: `{log['normalized_text']}`")
                if log.get('hybrid_commands'):
                    hybrid_preview = log['hybrid_commands'][:80] + '...' if len(log['hybrid_commands']) > 80 else log['hybrid_commands']
                    st.markdown(f"- 🔄 ハイブリッド: `{hybrid_preview}`")
                if log.get('ai_direct_commands'):
                    ai_preview = log['ai_direct_commands'][:80] + '...' if len(log['ai_direct_commands']) > 80 else log['ai_direct_commands']
                    st.markdown(f"- ⚡ AI単体: `{ai_preview}`")
                st.markdown("---")
    
    st.markdown("---")
    st.markdown("### 🤖 AI機能設定")
    
    st.markdown("**Gemini API キー**")
    if GEMINI_API_KEY:
        st.success("✅ APIキーが設定されています")
        
        # 利用可能なモデルをチェック
        if st.button("🔍 利用可能なモデルを確認"):
            with st.spinner("モデルをチェック中..."):
                import asyncio
                available_models = asyncio.run(check_available_models())
                
                if available_models:
                    st.success(f"✅ {len(available_models)}個のモデルが利用可能です")
                    with st.expander("📋 モデル一覧"):
                        for model in available_models:
                            st.code(model)
                else:
                    st.error("❌ 利用可能なモデルが見つかりませんでした")
                    st.info("APIキーが正しいか確認してください")
    else:
        st.warning("⚠️ APIキーが未設定です")
        st.info("Streamlit Cloudの場合: Settings → Secrets に `GEMINI_API_KEY = 'your-api-key'` を追加")
        st.info("ローカルの場合: 環境変数 `GEMINI_API_KEY` を設定")
    
    with st.expander("📖 Gemini APIキーの取得方法"):
        st.markdown("""
        1. [Google AI Studio](https://aistudio.google.com/app/apikey) にアクセス
        2. 「Create API Key」をクリック
        3. APIキーをコピー
        4. Streamlit Secretsまたは環境変数に設定
        
        **注意:** APIキーは `AIzaSy...` で始まる形式です
        """)
    
    st.markdown("---")
    st.markdown("### 📊 データ記録設定")
    
    enable_log = st.toggle(
        "📝 データをGoogle Sheetsに記録",
        value=st.session_state.enable_logging,
        help="入力文と生成結果を記録（機械学習研究用）"
    )
    st.session_state.enable_logging = enable_log
    
    if enable_log:
        st.success("✅ データ記録: 有効")
        
        with st.expander("📋 記録される情報"):
            st.markdown("""
            **記録項目:**
            1. タイムスタンプ
            2. ユーザー入力（元の文）
            3. AI正規化結果
            4. ハイブリッド版のコマンド
            5. AI単体版のコマンド
            6. エディション（統合版/Java版）
            
            **用途:**
            - 機械学習の訓練データ
            - 精度評価
            - モデル改善
            """)
        
        # Google Sheets設定状況
        if GSPREAD_AVAILABLE:
            if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
                st.success("✅ Google Sheets API: 設定済み")
                
                # ログダウンロードボタン
                if 'local_logs' in st.session_state and st.session_state.local_logs:
                    if st.button("💾 ローカルログをダウンロード"):
                        import json
                        log_json = json.dumps(st.session_state.local_logs, ensure_ascii=False, indent=2)
                        st.download_button(
                            label="📥 JSONファイルをダウンロード",
                            data=log_json,
                            file_name=f"command_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
            else:
                st.warning("⚠️ Google Sheets API: 未設定")
                st.info("Streamlit Secretsに認証情報を追加してください")
        else:
            st.warning("⚠️ gspreadライブラリがインストールされていません")
            st.info("requirements.txtに追加してください")
    else:
        st.info("ℹ️ データ記録: 無効")
    
    # ローカルログの表示
    if 'local_logs' in st.session_state and st.session_state.local_logs:
        with st.expander(f"📜 ローカルログ ({len(st.session_state.local_logs)}件)"):
            for i, log in enumerate(reversed(st.session_state.local_logs[-10:])):
                st.markdown(f"**{i+1}. {log['timestamp']}**")
                st.markdown(f"- 入力: `{log['user_input']}`")
                if log['normalized_text']:
                    st.markdown(f"- 正規化: `{log['normalized_text']}`")
                if log['hybrid_commands']:
                    st.markdown(f"- ハイブリッド: `{log['hybrid_commands'][:100]}...`")
                if log['ai_direct_commands']:
                    st.markdown(f"- AI単体: `{log['ai_direct_commands'][:100]}...`")
                st.markdown("---")
    
    st.markdown("---")
    st.markdown("### 📊 データファイル情報")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("アイテム数", f"{len(ITEMS)}個")
        st.metric("アイテムカテゴリ", f"{len(ITEM_CATEGORIES)}種類")
    with col2:
        st.metric("コマンド数", f"{len(COMMANDS)}個")
        st.metric("コマンドカテゴリ", f"{len(COMMAND_CATEGORIES)}種類")
    
    st.markdown("---")
    st.markdown("### 📁 ファイル構成")
    st.code("""
プロジェクトフォルダ/
├── app.py (このファイル)
├── item_data.py (アイテムデータ)
└── command_data.py (コマンドデータ)
    """)
    
    st.markdown("---")
    st.markdown("### 📚 その他の機能（準備中）")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📖 サイトの使い方"):
            st.info("使い方ページは準備中です")
        if st.button("📈 コマンド履歴"):
            st.info("履歴機能は準備中です")
    
    with col2:
        if st.button("🖼 背景を変更"):
            st.info("背景変更機能は準備中です")
        if st.button("📝 パッチノート"):
            st.info("パッチノートは準備中です")

# フッター
st.markdown("---")
st.markdown("*Minecraftコマンド生成ツール - Powered by Streamlit*")
st.markdown("🎮 統合版・Java版両対応")
