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

# AI直接生成プロンプト
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

# データ読み込み部分
current_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
files_in_dir = os.listdir(current_dir)

ITEMS = {}
ITEM_CATEGORIES = []
EFFECTS = {}
EFFECT_CATEGORIES = []
MOBS = {}
MOB_CATEGORIES = []
STRUCTURES = {}
STRUCTURE_CATEGORIES = []
COMMANDS = []
COMMAND_CATEGORIES = []

load_status = {
    'items': False,
    'effects': False,
    'commands': False,
    'mobs': False,
    'structures': False,
    'items_error': '',
    'effects_error': '',
    'commands_error': '',
    'mobs_error': '',
    'structures_error': ''
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

# effect_data.py の読み込み
try:
    effect_data_path = os.path.join(current_dir, 'effect_data.py')
    
    if os.path.exists(effect_data_path):
        spec = importlib.util.spec_from_file_location("effect_data", effect_data_path)
        effect_data = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(effect_data)
        
        effects_dict = getattr(effect_data, 'effects', None) or getattr(effect_data, 'EFFECTS', {})
        EFFECTS = effects_dict
        
        if EFFECTS:
            EFFECT_CATEGORIES = list(set([effect.get('category', 'その他') for effect in EFFECTS.values()]))
            EFFECT_CATEGORIES.sort()
        
        load_status['effects'] = True
        load_status['effects_count'] = len(EFFECTS)
    else:
        load_status['effects_error'] = f"ファイルが見つかりません: {effect_data_path}"
        
except Exception as e:
    load_status['effects_error'] = str(e)

# mob_data.py の読み込み
try:
    mob_data_path = os.path.join(current_dir, 'mob_data.py')
    
    if os.path.exists(mob_data_path):
        spec = importlib.util.spec_from_file_location("mob_data", mob_data_path)
        mob_data = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mob_data)
        
        mobs_dict = getattr(mob_data, 'mobs', None) or getattr(mob_data, 'MOBS', {})
        MOBS = mobs_dict
        
        if MOBS:
            MOB_CATEGORIES = list(set([mob.get('category', 'その他') for mob in MOBS.values()]))
            MOB_CATEGORIES.sort()
        
        load_status['mobs'] = True
        load_status['mobs_count'] = len(MOBS)
    else:
        load_status['mobs_error'] = f"ファイルが見つかりません: {mob_data_path}"
        
except Exception as e:
    load_status['mobs_error'] = str(e)

# structure_data.py の読み込み
try:
    structure_data_path = os.path.join(current_dir, 'structure_data.py')
    
    if os.path.exists(structure_data_path):
        spec = importlib.util.spec_from_file_location("structure_data", structure_data_path)
        structure_data = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(structure_data)
        
        structures_dict = getattr(structure_data, 'structures', None) or getattr(structure_data, 'STRUCTURES', {})
        STRUCTURES = structures_dict
        
        if STRUCTURES:
            STRUCTURE_CATEGORIES = list(set([s.get('category', 'その他') for s in STRUCTURES.values()]))
            STRUCTURE_CATEGORIES.sort()
        
        load_status['structures'] = True
        load_status['structures_count'] = len(STRUCTURES)
    else:
        load_status['structures_error'] = f"ファイルが見つかりません: {structure_data_path}"
        
except Exception as e:
    load_status['structures_error'] = str(e)

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

# ========== コマンド検索 ==========    
def search_commands(query, edition):
    """
    ユーザーの入力からgiveコマンドのみを検索
    """
    global ITEMS, EFFECTS, MOBS, STRUCTURES, COMMANDS
    
    if not COMMANDS:
        return []
    
    results = []
    query_lower = query.lower()
    
    # giveコマンド以外のキーワードチェック
    non_give_keywords = ['エフェクト', '効果', 'テレポート', '移動', '天候', '時間', 'モブ', '召喚']
    if any(kw in query_lower for kw in non_give_keywords):
        return []
    
    # ターゲットセレクターの抽出
    target = '@s'
    if '@a' in query_lower or 'みんな' in query_lower or '全員' in query_lower or '全プレイヤー' in query_lower:
        target = '@a'
    elif '@r' in query_lower or 'ランダム' in query_lower:
        target = '@r'
    elif '@p' in query_lower or '最も近い' in query_lower:
        target = '@p'
    elif '自分' in query_lower or 'me' in query_lower:
        target = '@s'
    
    # 数量の抽出
    import re
    quantity = 1
    
    numbers = re.findall(r'\d+', query)
    if numbers:
        quantity = int(numbers[0])
    elif '大量' in query_lower or 'たくさん' in query_lower or 'いっぱい' in query_lower or 'スタック' in query_lower:
        quantity = 64
    elif '半スタック' in query_lower:
        quantity = 32
    elif '少し' in query_lower or '数個' in query_lower or 'ちょっと' in query_lower:
        quantity = 5
    
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
            
            # アイテムIDの置き換え
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
                    
                    cmd_text = cmd_template.replace('{item_id}', item_id)
                    cmd_text = cmd_text.replace('{target}', target)
                    cmd_text = cmd_text.replace('@s', target)
                    
                    if '/give' in cmd_text and item_id:
                        if not re.search(r'\d+\s*$', cmd_text):
                            cmd_text = f"{cmd_text} {quantity}"
                        else:
                            cmd_text = re.sub(r'\d+\s*$', str(quantity), cmd_text)
                    
                    cmd_copy['cmd'] = cmd_text
                    cmd_copy['item_name'] = matched_item.get('name', '')
                    cmd_copy['matched_item_key'] = item_key
                    
                    desc = cmd_copy.get('desc', '')
                    if '{item}' in desc:
                        cmd_copy['desc'] = desc.replace('{item}', matched_item.get('name', ''))
                else:
                    cmd_copy['cmd'] = cmd_template
            else:
                cmd_text = cmd_template
                
                if '{target}' in cmd_text:
                    cmd_text = cmd_text.replace('{target}', target)
                
                if '@s' in cmd_text:
                    cmd_text = cmd_text.replace('@s', target)
                
                cmd_copy['cmd'] = cmd_text
            
            cmd_copy['cmd_template'] = cmd_template
            results.append(cmd_copy)
    
    return results

# ========== セッションステートの初期化 ==========
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
if 'batch_results' not in st.session_state:
    st.session_state.batch_results = []

# ========== メイン画面 ==========
st.title("⛏️ Minecraftコマンド生成ツール")
st.markdown("---")

# サイドバーメニュー
st.sidebar.markdown("### 🎮 メニュー")
menu = st.sidebar
menu = st.sidebar.radio(
    "機能選択",
    ["🏠 ホーム", "🛠 コマンド生成", "⚙️ 設定", "🧪 実験モード"],
    key="main_menu",
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**エディション:** {st.session_state.edition}")

# ========== ホーム画面 ==========
if menu == "🏠 ホーム":
    st.header("🏠 ホームメニュー")
    st.success("✅ システム稼働中")
    
    st.markdown("""
    ### 📚 機能一覧
    - 🛠 **コマンド生成**: 個別テスト
    - 🧪 **実験モード**: 一括バッチ処理（最大100件）
    - ⚙️ **設定**: API設定・データ記録
    """)

# ========== コマンド生成画面 ==========
elif menu == "🛠 コマンド生成":
    st.header("🛠 コマンド生成（個別テスト）")
    
    user_input = st.text_area(
        "入力",
        placeholder="例: パンが欲しい",
        height=100
    )
    
    if st.button("🚀 生成", type="primary"):
        if user_input:
            with st.spinner("処理中..."):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### ハイブリッド版")
                    try:
                        normalized, model = asyncio.run(normalize_with_gemini(user_input))
                        if normalized:
                            st.success(f"正規化: {normalized}")
                            candidates = search_commands(normalized, st.session_state.edition)
                            for cmd in candidates:
                                st.code(cmd['cmd'])
                    except Exception as e:
                        st.error(f"エラー: {e}")
                
                with col2:
                    st.markdown("### AI単体版")
                    try:
                        commands, model = asyncio.run(generate_command_directly(user_input, st.session_state.edition))
                        if commands:
                            for cmd in commands.split('\n'):
                                if cmd.strip():
                                    st.code(cmd.strip())
                    except Exception as e:
                        st.error(f"エラー: {e}")

# ========== 設定画面 ==========
elif menu == "⚙️ 設定":
    st.header("⚙️ 設定")
    
    edition = st.radio(
        "エディション",
        ["統合版", "Java版"],
        index=0 if st.session_state.edition == "統合版" else 1
    )
    st.session_state.edition = edition
    
    st.markdown("---")
    
    enable_log = st.toggle(
        "Google Sheetsに自動記録",
        value=st.session_state.enable_logging
    )
    st.session_state.enable_logging = enable_log
    
    if GEMINI_API_KEY:
        st.success("✅ Gemini API: 設定済み")
    else:
        st.error("❌ Gemini API: 未設定")

# ========== 🧪 実験モード ==========
elif menu == "🧪 実験モード":
    st.header("🧪 実験モード - 一括バッチ処理")
    
    st.warning("⚠️ **研究者向け機能**: 最大100件のテストケースを自動実行し、結果を記録します")
    
    if not GEMINI_API_KEY:
        st.error("❌ Gemini APIキーが必要です")
        st.stop()
    
    # テストケース入力
    st.markdown("### 📋 テストケース")
    
    default_cases = """ステーキがほしい
ステーキをください
ステーキを10個
パンがほしい
パンを8個ください
焼き鳥がほしい
焼き鳥を16個
ベイクドポテトがほしい
ベイクドポテトを12個
金のリンゴがほしい
金のリンゴをください
金のリンゴを3個
エンチャントされた金のリンゴがほしい
ニンジンがほしい
ニンジンを16個
ダイヤモンドのツルハシがほしい
ダイヤモンドの剣を1個
松明を64個ください
みんなにパンを配る
自分に鉄インゴットを32個"""
    
    test_cases_text = st.text_area(
        "テストケース（1行1ケース、最大100件）",
        value=default_cases,
        height=400
    )
    
    test_cases = [line.strip() for line in test_cases_text.split('\n') if line.strip()]
    test_cases = test_cases[:100]  # 最大100件に制限
    
    st.info(f"📊 **{len(test_cases)}件** のテストケース")
    
    # 実行設定
    st.markdown("---")
    st.markdown("### ⚙️ 実行設定")
    
    col_set1, col_set2, col_set3 = st.columns(3)
    
    with col_set1:
        delay = st.slider("間隔（秒）", 0.0, 5.0, 1.0, 0.5)
    
    with col_set2:
        auto_log = st.checkbox("自動記録", value=st.session_state.enable_logging)
    
    with col_set3:
        show_detail = st.checkbox("詳細表示", value=False)
    
    # 実行ボタン
    st.markdown("---")
    
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        start_btn = st.button("🚀 一括実行開始", type="primary", use_container_width=True)
    
    with col_btn2:
        if st.button("📥 結果ダウンロード", use_container_width=True):
            if st.session_state.batch_results:
                result_json = json.dumps(st.session_state.batch_results, ensure_ascii=False, indent=2)
                st.download_button(
                    "💾 JSON保存",
                    data=result_json,
                    file_name=f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
    
    with col_btn3:
        if st.button("🗑️ 結果クリア", use_container_width=True):
            st.session_state.batch_results = []
            st.success("✅ クリア完了")
            st.rerun()
    
    # バッチ実行
    if start_btn:
        st.markdown("---")
        st.markdown("## 🔄 実行中...")
        
        batch_results = []
        success_count = 0
        error_count = 0
        
        # プログレスバー
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 統計表示
        stats_container = st.container()
        
        # 結果詳細表示
        if show_detail:
            detail_container = st.expander("📋 詳細ログ", expanded=True)
        
        for idx, test_input in enumerate(test_cases):
            # 進捗更新
            progress = (idx + 1) / len(test_cases)
            progress_bar.progress(progress)
            status_text.markdown(f"**{idx + 1}/{len(test_cases)}** - `{test_input}`")
            
            result = {
                "test_id": idx + 1,
                "input": test_input,
                "timestamp": datetime.now().isoformat(),
                "edition": st.session_state.edition
            }
            
            try:
                # ハイブリッド版
                hybrid_start = time.time()
                normalized, model = asyncio.run(normalize_with_gemini(test_input))
                
                if normalized:
                    result["normalized"] = normalized
                    result["model"] = model
                    
                    candidates = search_commands(normalized, st.session_state.edition)
                    
                    if candidates:
                        cmds = [c['cmd'] for c in candidates]
                        result["hybrid_commands"] = cmds
                        result["hybrid_time"] = time.time() - hybrid_start
                    else:
                        result["hybrid_error"] = "コマンド未検出"
                else:
                    result["hybrid_error"] = "正規化失敗"
                
                result["hybrid_time"] = time.time() - hybrid_start
                
                # AI単体版
                ai_start = time.time()
                ai_commands, ai_model = asyncio.run(generate_command_directly(test_input, st.session_state.edition))
                
                if ai_commands:
                    result["ai_commands"] = [c.strip() for c in ai_commands.split('\n') if c.strip()]
                    result["ai_time"] = time.time() - ai_start
                else:
                    result["ai_error"] = "生成失敗"
                    result["ai_time"] = time.time() - ai_start
                
                # 成功カウント
                if "hybrid_commands" in result or "ai_commands" in result:
                    success_count += 1
                else:
                    error_count += 1
                
                # Google Sheetsに記録
                if auto_log:
                    log_research_data(
                        test_input,
                        result.get("normalized", ""),
                        " | ".join(result.get("hybrid_commands", [])),
                        " | ".join(result.get("ai_commands", [])),
                        st.session_state.edition,
                        hybrid_time=result.get("hybrid_time"),
                        ai_time=result.get("ai_time"),
                        hybrid_error=result.get("hybrid_error"),
                        ai_error=result.get("ai_error"),
                        used_model=result.get("model")
                    )
                
                # 詳細表示
                if show_detail:
                    with detail_container:
                        st.markdown(f"**#{idx + 1}** `{test_input}`")
                        col_d1, col_d2 = st.columns(2)
                        with col_d1:
                            if "hybrid_commands" in result:
                                for cmd in result["hybrid_commands"]:
                                    st.code(cmd, language="bash")
                        with col_d2:
                            if "ai_commands" in result:
                                for cmd in result["ai_commands"]:
                                    st.code(cmd, language="bash")
                        st.markdown("---")
                
            except Exception as e:
                result["error"] = str(e)
                error_count += 1
            
            batch_results.append(result)
            
            # 統計更新
            with stats_container:
                col_s1, col_s2, col_s3 = st.columns(3)
                with col_s1:
                    st.metric("処理済み", f"{idx + 1}/{len(test_cases)}")
                with col_s2:
                    st.metric("成功", success_count)
                with col_s3:
                    st.metric("エラー", error_count)
            
            # 待機
            time.sleep(delay)
        
        # 結果保存
        st.session_state.batch_results = batch_results
        
        # 完了メッセージ
        progress_bar.progress(1.0)
        status_text.markdown("✅ **完了！**")
        
        st.success(f"🎉 バッチ処理完了: {len(test_cases)}件処理（成功: {success_count}, エラー: {error_count}）")
        
        # 結果サマリー
        st.markdown("---")
        st.markdown("## 📊 結果サマリー")
        
        avg_hybrid_time = sum([r.get("hybrid_time", 0) for r in batch_results]) / len(batch_results)
        avg_ai_time = sum([r.get("ai_time", 0) for r in batch_results]) / len(batch_results)
        
        col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
        
        with col_sum1:
            st.metric("平均処理時間（ハイブリッド）", f"{avg_hybrid_time:.2f}秒")
        with col_sum2:
            st.metric("平均処理時間（AI単体）", f"{avg_ai_time:.2f}秒")
        with col_sum3:
            st.metric("成功率", f"{success_count/len(test_cases)*100:.1f}%")
        with col_sum4:
            st.metric("総処理時間", f"{sum([r.get('hybrid_time', 0) + r.get('ai_time', 0) for r in batch_results]):.1f}秒")

# フッター
st.markdown("---")
st.markdown("*Minecraft実験システム - バッチ処理対応版*")
        """)

# フッター
st.markdown("---")
st.markdown("*Minecraftコマンド生成ツール - 研究用データ収集機能付き*")
st.markdown("🎮 統合版・Java版両対応 | 📊 研究データ自動記録")
