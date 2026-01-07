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
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent",
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
例:
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
giveコマンド以外(エフェクト付与、テレポート、天候変更、モブ召喚など)は「対象外」と出力
### 【推論の優先順位】
1. 具体的なアイテム名がある場合はそれを優先。
2. 「〜したい」「〜がない」という表現から、それを解決する最も強力/一般的なアイテムを選択。
3. 数量の指定がない場合、そのアイテムの一般的な使用単位(ツールなら1、消耗品なら複数)を割り当てる。

### 【入力】
{user_input}

### 【正規化された出力】
"""

# AI直接生成プロンプト
DIRECT_GENERATION_PROMPT = """あなたはMinecraftのコマンド生成AIです。ユーザーの自然言語入力から、直接Minecraftコマンドを生成してください。

【重要ルール】
- コマンドのみを出力(説明文や前置きは不要)
- 複数コマンドの場合は改行で区切る
- **giveコマンドのみ**を出力(/give @s <item_id> <amount>)
- 入力された分から意図を理解し、ユーザーが欲しい適切なコマンドを出力

【エディション】
現在のエディション: {edition}
※統合版の場合は統合版のコマンド形式を、Java版の場合はJava版の形式を使用

【入力】
{user_input}

【生成されたコマンド】

"""

# 一括処理用プロンプト
BATCH_NORMALIZATION_PROMPT = """あなたはMinecraftの「give」コマンド生成に特化した自然言語正規化エンジンです。
複数のユーザー入力を一括で処理し、それぞれを正規化してください。

### 【正規化形式】
各行ごとに: [対象]に[アイテム名]を[数量]個与える

### 【ルール】
- 各入力行を個別に処理
- 出力は入力と同じ行数
- 各行は独立した正規化結果
- 説明や挨拶は禁止
- 処理できない行は「対象外」と出力

### 【入力リスト】
{user_inputs}

### 【正規化された出力リスト】
"""

# ========== 研究用データ記録関数(拡張版) ==========
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
        
        # データ行を作成(研究用に拡張)
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

# ========== ローカルログ記録(フォールバック) ==========
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
    ローカルファイルに記録(Google Sheets利用不可の場合)
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

# ========== AI一括正規化関数 ==========
async def batch_normalize_with_gemini(user_inputs_list):
    """
    複数の入力を一括で正規化
    """
    if not GEMINI_API_KEY:
        return None, None
    
    import aiohttp
    
    # 入力リストを文字列に変換
    inputs_text = "\n".join([f"{i+1}. {inp}" for i, inp in enumerate(user_inputs_list)])
    
    for endpoint in GEMINI_ENDPOINTS:
        try:
            prompt = BATCH_NORMALIZATION_PROMPT.replace("{user_inputs}", inputs_text)
            
            headers = {"Content-Type": "application/json"}
            
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 2000,
                }
            }
            
            url = f"{endpoint}?key={GEMINI_API_KEY}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=60)) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
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
    if '@a' in query_lower or 'みんな' in query_lower or '全員' in query_lower or '全プレイヤー' in query_lower or 'ぜんぷれいやー' in query_lower or '全てのプレイヤー' in query_lower:
        target = '@a'
    elif '@r' in query_lower or 'ランダム' in query_lower or 'らんだむ' in query_lower:
        target = '@r'
    elif '@p' in query_lower or '最も近い' in query_lower or 'もっともちかい' in query_lower or '一番近い' in query_lower:
        target = '@p'
    elif '@e' in query_lower or 'エンティティ' in query_lower or 'えんてぃてぃ' in query_lower or '全てのエンティティ' in query_lower:
        target = '@e'
    elif '自分' in query_lower or 'me' in query_lower or 'じぶん' in query_lower:
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
    
    COMMANDS = [cmd for cmd in COMMANDS if 'give' in cmd.get('key', '').lower() or 
            'give' in str(cmd.get('template', '')).lower()]
    
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
menu = st.sidebar.radio(
    "機能選択",
    ["🏠 ホーム", "🛠 コマンド生成", "🧪 実験者メニュー", "📘 アイテム図鑑", "⚙️ 設定"],
    key="main_menu",
    label_visibility="collapsed"
)

# データ読み込み状況を表示
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 データ状況")
st.sidebar.markdown(f"**アイテム:** {len(ITEMS)}個")
st.sidebar.markdown(f"**モブ:** {len(MOBS)}個")
st.sidebar.markdown(f"**コマンド:** {len(COMMANDS)}個")
st.sidebar.markdown(f"**エディション:** {st.session_state.edition}")

# ========== ホーム画面 ==========
if menu == "🏠 ホーム":
    st.header("🏠 ホームメニュー")
    
    if load_status['items'] and load_status['commands']:
        st.success(f"✅ データ読み込み成功!")
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
        - 🧪 **実験者メニュー**: 最大100件の一括処理
        - 📘 **アイテム図鑑**: アイテム一覧と検索
        - ⚙️ **設定**: バージョン選択など
        """)
    
    with col2:
        st.markdown("### 🎯 使い方")
        st.markdown("""
        1. 左メニューから機能を選択
        2. やりたいことを日本語で入力
        3. コマンドが自動生成されます
        4. コピー&ペーストして使用
        """)
    
    st.markdown("---")
    st.markdown("### 📊 研究データ収集について")
    
    if st.session_state.enable_logging:
        st.info("✅ **データ記録: 有効** - あなたの入力と生成結果が研究用に記録されます")
    else:
        st.warning("⚠️ **データ記録: 無効** - 設定ページで有効にできます")

# ========== 実験者メニュー画面 ==========
elif menu == "🧪 実験者メニュー":
    st.header("🧪 実験者メニュー - 一括処理")
    st.info("💡 最大100件の命令を一度に処理できます")
    
    if not GEMINI_API_KEY:
        st.error("❌ Gemini APIキーが設定されていません")
        st.stop()
    
    st.markdown("---")
    st.markdown("### 📝 一括入力")
    st.caption("1行に1つの命令を入力してください(最大100行)")
    
    # サンプルテキスト
    sample_text = """ステーキがほしい
ステーキをください
ステーキを10個
パンがほしい
パンを8個ください
焼き鳥がほしい
焼き鳥を16個
ベイクドポテトがほしい
ベイクドポテトを12個
金のリンゴがほしい"""
    
    col_sample1, col_sample2 = st.columns([3, 1])
    with col_sample1:
        batch_input = st.text_area(
            "命令リスト",
            height=300,
            placeholder=sample_text,
            help="1行に1命令、最大100行まで",
            key="batch_input_area"
        )
    
    with col_sample2:
        st.markdown("**📋 サンプル**")
        if st.button("サンプルを読み込む", use_container_width=True):
            st.session_state.batch_input_area = sample_text
            st.rerun()
        
        st.markdown("---")
        st.markdown("**統計**")
        if batch_input:
            lines = [line.strip() for line in batch_input.split('\n') if line.strip()]
            st.metric("入力行数", f"{len(lines)}行")
            if len(lines) > 100:
                st.error("❌ 100行を超えています")
        else:
            st.metric("入力行数", "0行")
    
    # 処理ボタン
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        process_btn = st.button("🚀 一括処理開始", type="primary", use_container_width=True)
    with col_btn2:
        if st.session_state.batch_results:
            export_btn = st.button("💾 結果をエクスポート", use_container_width=True)
        else:
            st.button("💾 結果をエクスポート", use_container_width=True, disabled=True)
    with col_btn3:
        clear_btn = st.button("🗑️ クリア", use_container_width=True)
        if clear_btn:
            st.session_state.batch_results = []
            st.rerun()
    
    if process_btn and batch_input:
        lines = [line.strip() for line in batch_input.split('\n') if line.strip()]
        
        if len(lines) > 100:
            st.error("❌ 一度に処理できるのは100行までです")
            st.stop()
        
        if len(lines) == 0:
            st.warning("⚠️ 処理する命令を入力してください")
            st.stop()
        
        st.markdown("---")
        st.markdown("## 🔄 処理中...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        import asyncio
        
        start_time = time.time()
        
        # 一括正規化
        status_text.text("📡 AI正規化中...")
        normalized_result, model_name = asyncio.run(batch_normalize_with_gemini(lines))
        
        if normalized_result:
            normalized_lines = [line.strip() for line in normalized_result.split('\n') if line.strip()]
            
            # 行数が一致しない場合の処理
            if len(normalized_lines) != len(lines):
                st.warning(f"⚠️ 正規化結果の行数が異なります (入力: {len(lines)}行, 出力: {len(normalized_lines)}行)")
                # 不足分を「対象外」で埋める
                while len(normalized_lines) < len(lines):
                    normalized_lines.append("対象外")
            
            results = []
            
            for i, (original, normalized) in enumerate(zip(lines, normalized_lines)):
                progress = (i + 1) / len(lines)
                progress_bar.progress(progress)
                status_text.text(f"処理中... {i+1}/{len(lines)}")
                
                if normalized == "対象外":
                    results.append({
                        'index': i + 1,
                        'original': original,
                        'normalized': normalized,
                        'commands': [],
                        'status': 'skipped'
                    })
                    continue
                
                # コマンド検索
                candidates = search_commands(normalized, st.session_state.edition)
                
                commands_list = []
                if candidates:
                    for cmd in candidates:
                        cmd_text = cmd.get('cmd', '')
                        if cmd_text:
                            commands_list.append(cmd_text)
                
                results.append({
                    'index': i + 1,
                    'original': original,
                    'normalized': normalized,
                    'commands': commands_list,
                    'status': 'success' if commands_list else 'no_command'
                })
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            st.session_state.batch_results = results
            
            progress_bar.progress(1.0)
            status_text.empty()
            
            st.success(f"✅ 処理完了! ({processing_time:.2f}秒)")
            
            # 統計情報
            success_count = sum(1 for r in results if r['status'] == 'success')
            skipped_count = sum(1 for r in results if r['status'] == 'skipped')
            failed_count = sum(1 for r in results if r['status'] == 'no_command')
            
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            with col_stat1:
                st.metric("総数", f"{len(results)}件")
            with col_stat2:
                st.metric("成功", f"{success_count}件", delta=None, delta_color="normal")
            with col_stat3:
                st.metric("スキップ", f"{skipped_count}件")
            with col_stat4:
                st.metric("失敗", f"{failed_count}件")
            
        else:
            st.error("❌ AI正規化に失敗しました")
    
    # 結果表示
    if st.session_state.batch_results:
        st.markdown("---")
        st.markdown("## 📊 処理結果")
        
        # フィルター
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            filter_option = st.selectbox(
                "表示フィルター",
                ["すべて", "成功のみ", "失敗のみ", "スキップのみ"]
            )
        
        with col_filter2:
            show_details = st.checkbox("詳細を表示", value=True)
        
        filtered_results = st.session_state.batch_results
        if filter_option == "成功のみ":
            filtered_results = [r for r in filtered_results if r['status'] == 'success']
        elif filter_option == "失敗のみ":
            filtered_results = [r for r in filtered_results if r['status'] == 'no_command']
        elif filter_option == "スキップのみ":
            filtered_results = [r for r in filtered_results if r['status'] == 'skipped']
        
        # 結果リスト表示
        for result in filtered_results:
            with st.container(border=True):
                col_res1, col_res2 = st.columns([1, 5])
                
                with col_res1:
                    if result['status'] == 'success':
                        st.markdown("### ✅")
                    elif result['status'] == 'skipped':
                        st.markdown("### ⏭️")
                    else:
                        st.markdown("### ❌")
                    st.caption(f"#{result['index']}")
                
                with col_res2:
                    st.markdown(f"**入力:** {result['original']}")
                    
                    if show_details:
                        st.markdown(f"*正規化:* {result['normalized']}")
                    
                    if result['commands']:
                        for cmd in result['commands']:
                            st.code(cmd, language='bash')
                    elif result['status'] == 'skipped':
                        st.info("⏭️ スキップ: giveコマンド対象外")
                    else:
                        st.warning("⚠️ コマンドが見つかりませんでした")
        
        # エクスポート機能
        if 'export_btn' in locals() and export_btn:
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'edition': st.session_state.edition,
                'total': len(st.session_state.batch_results),
                'results': st.session_state.batch_results
            }
            
            export_json = json.dumps(export_data, ensure_ascii=False, indent=2)
            
            st.download_button(
                label="📥 JSONダウンロード",
                data=export_json,
                file_name=f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )

# ========== コマンド生成画面 ========== (既存のコード、変更なし)
elif menu == "🛠 コマンド生成":
    st.header("🛠 コマンド生成")
    
    if not COMMANDS:
        st.error("❌ コマンドデータが読み込まれていません")
        st.stop()
    
    # (以降は元のコマンド生成画面のコードをそのまま使用)
    st.markdown("### 生成モード選択")
    col_mode1, col_mode2, col_mode3 = st.columns(3)
    
    with col_mode1:
        mode_both = st.button(
            "⚖️ 両方比較(推奨)",
            type="primary" if st.session_state.generation_mode == 'both' else "secondary",
            use_container_width=True,
            help="ハイブリッド版とAI単体版を同時に表示"
        )
        if mode_both:
            st.session_state.generation_mode = 'both'
    
    with col_mode2:
        mode_hybrid = st.button(
            "📊 ハイブリッド版のみ",
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
    
    if st.session_state.generation_mode == 'both':
        st.info("⚖️ **比較モード**: ハイブリッド版とAI単体版を同時表示")
    elif st.session_state.generation_mode == 'hybrid':
        st.info("📊 **ハイブリッド版**: AI正規化 → ルールベース生成(精度重視)")
    else:
        st.info("🚀 **AI単体版**: AIが直接コマンドを生成(柔軟性重視)")
    
    st.markdown("---")
    
    if not GEMINI_API_KEY:
        st.error("❌ Gemini APIキーが設定されていません。AI機能を使用するには設定が必要です。")
        st.stop()
    
    st.markdown("### やりたいことを自然な日本語で入力してください")
    
    user_input = st.text_area(
        "入力例",
        value=st.session_state.user_input,
        placeholder="例:\n- パンが欲しい\n- ダイヤのツルハシちょうだい\n- みんなに松明を大量に配る\n- 自分に金のリンゴを5個",
        height=100,
        key="command_input"
    )
    
    generate_btn = st.button("🚀 コマンド生成", type="primary", use_container_width=True)
    
    # (残りのコマンド生成ロジックは元のコードをそのまま使用)

# ========== 設定画面 ========== (既存のコード、変更なし)
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
    st.markdown("### 📊 研究用データ記録設定")
    
    enable_log = st.toggle(
        "📊 データをGoogle Sheetsに記録",
        value=st.session_state.enable_logging,
        help="入力文と生成結果を記録(機械学習研究用)"
    )
    st.session_state.enable_logging = enable_log
    
    if enable_log:
        st.success("✅ データ記録: 有効")
    else:
        st.info("ℹ️ データ記録: 無効")

# フッター
st.markdown("---")
st.markdown("*Minecraftコマンド生成ツール - 研究用データ収集機能付き*")
st.markdown("🎮 統合版・Java版両対応 | 📊 研究データ自動記録 | 🧪 実験者メニュー搭載")
